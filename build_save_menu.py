#!/usr/bin/env python3
"""
Save/load screen: "2面" -> "St2".

The routine $87:E8AE (one copy per file: $87:E8AE / $87:E911 / $87:E974)
puts the cursor at $15, reads the stage the file has reached, then:
    0      -> "なし" ($87:89EB, already translated as "None")
    $18    -> "EX"     ($87:8AE5)
    else   -> 2-digit number ($80:F6E8, X=2) then "面" ($87:89C1)
The number is one pair tile (" 2" = blank+2) and 面 one 16x16 tile: that
leaves only 2 tiles, and "St" in front of the number would give "St 2".

In each copy, the number + 面 sequence (29 bytes from the LDX #$0002) is
replaced by a JSL to a small routine at $BF:FC00 that prints a precomposed
half-width string "St1" .. "St23" (4 characters, padded with a space =
exactly the width of "None" / "2面", so no ghosting).

apply(rom) is called by build_full_translation.py (after BT.apply).
"""
import struct

from build_scene_injection import encode_hw

CODE_FILE = 0x1FFC00            # $BF:FC00
CODE_SNES = 0xBFFC00
AREA_END = 0x1FFE00
MAX_STAGE = 23                  # $18 = EX, handled by the game
WIDTH = 4                       # half-width chars: "None" = 2 pair tiles

SITES = [0x87E8C4, 0x87E927, 0x87E98A]   # the LDX #$0002 of each copy
ORIG = bytes.fromhex("a20200" "22e8f680" "e220" "48" "a9c18509" "a9898" "50a" "a987850b"
                     "68" "c220" "22a7f480")


def _file(snes):
    return ((snes >> 16) & 0x7F) * 0x8000 + (snes & 0x7FFF)


def apply(rom):
    strings = bytearray()
    for n in range(1, MAX_STAGE + 1):
        ids = encode_hw(f"St{n}".ljust(WIDTH)) + [0xFFFF]
        strings += b"".join(struct.pack("<H", i) for i in ids)
    rec = 2 * (WIDTH + 1)                                   # 10 bytes per string

    table = CODE_SNES + 0x40
    base = (table & 0xFFFF) - rec                           # stage 1 = first string
    code = bytes([
        0x0A,                       # ASL A          ; 2n
        0x48,                       # PHA
        0x0A, 0x0A,                 # ASL A x2       ; 8n
        0x18, 0x63, 0x01,           # CLC / ADC 1,S  ; 10n
        0xFA,                       # PLX            ; (drops 2n)
        0x18, 0x69, base & 0xFF, base >> 8,   # CLC / ADC #base
        0xE2, 0x20,                 # SEP #$20
        0x85, 0x09,                 # STA $09
        0xEB,                       # XBA
        0x85, 0x0A,                 # STA $0A
        0xA9, table >> 16,          # LDA #$BF
        0x85, 0x0B,                 # STA $0B
        0xC2, 0x20,                 # REP #$20
        0x22, 0xA7, 0xF4, 0x80,     # JSL $80:F4A7
        0x6B,                       # RTL
    ])
    assert len(code) <= 0x40 and rec == 10
    blob = code.ljust(0x40, b"\xFF") + strings
    if CODE_FILE + len(blob) > AREA_END:
        raise SystemExit("build_save_menu: area at $BF:FC00 too small")
    if any(b not in (0x00, 0xFF) for b in rom[CODE_FILE:CODE_FILE + len(blob)]):
        raise SystemExit("build_save_menu: $BF:FC00 already in use")
    rom[CODE_FILE:CODE_FILE + len(blob)] = blob

    for s in SITES:
        o = _file(s)
        if bytes(rom[o:o + len(ORIG)]) != ORIG:
            raise SystemExit(f"build_save_menu: unexpected code at ${s >> 16:02X}:{s & 0xFFFF:04X}")
        patch = bytes([0x22, CODE_SNES & 0xFF, (CODE_SNES >> 8) & 0xFF, CODE_SNES >> 16])
        rom[o:o + len(ORIG)] = patch + b"\xEA" * (len(ORIG) - len(patch))
    return MAX_STAGE
