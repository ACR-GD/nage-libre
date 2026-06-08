#!/usr/bin/env python3
"""
Patch prologue screen 1 — SAFE approach.

After $80:F8D8, replace exactly 30 tilemap entries at $7F:65E2
(WRAM offset $0122): 16 cells visual line 1 + 14 cells line 2.
This block includes $7F:6602 (offset $0142, words 16–29) but does NOT
touch $01A2+ (row 2 tilemap / screen-2 preload / border).

See docs/prologue_text_engine.md § Architecture confirmée.
"""
from pathlib import Path

from patch_prologue_v3 import (
    char_id_to_rom,
    encode_to_slots,
    find_safe_ids,
    fix_checksum,
    make_pair_tile,
    ScatterAllocator,
)

ROM_PATH = Path(__file__).parent / "Nage Libre - Seijaku no Suishin (Japan).sfc"
OUT_PATH = Path(__file__).parent / "nage-libre-en-prologue-test.sfc"

HOOK_ROM = 0x01F8E3
HOOK_POINT = 0x0180FF
HOOK_BANK = 0x83
HOOK_ADDR = 0xF8E3
MIN_FONT_ID = 0x0100

WRAM_BASE = 0x7F65E2  # $64C0 + $0122
SLOT_L1 = 16
SLOT_L2 = 14
SLOT_TOTAL = SLOT_L1 + SLOT_L2

# 16 + 14 VWF slots — full sentence with JP-style ellipsis tiles
LINE1 = "  In a distant world,"
LINE2 = " a voice echoes\u2026\u2026"


def safe_pair_ids(rom):
    return [cid for cid in find_safe_ids(rom) if cid >= MIN_FONT_ID]


def assemble_hook(text_ids):
    code = bytearray()
    code += bytes([0x22, 0xD8, 0xF8, 0x80])  # JSL $80:F8D8
    code += bytes([0x08, 0xC2, 0x20, 0x48])  # PHP REP #$20 PHA

    code += bytes([0xAF, 0x02, 0x66, 0x7F])  # LDA.l $7F:6602
    code += bytes([0xC9, 0x5A, 0x07])        # CMP #$075A
    bne = len(code)
    code += bytes([0xD0, 0x00])

    code += bytes([0xAF, 0x04, 0x66, 0x7F])  # LDA.l $7F:6604
    code += bytes([0xC9, 0x2A, 0x00])        # CMP #$002A (く)
    bne2 = len(code)
    code += bytes([0xD0, 0x00])

    for i, cid in enumerate(text_ids):
        addr = WRAM_BASE + i * 2
        code += bytes([0xA9, cid & 0xFF, (cid >> 8) & 0xFF])
        code += bytes([0x8F, addr & 0xFF, (addr >> 8) & 0xFF, (addr >> 16) & 0xFF])

    skip = len(code)
    code[bne + 1] = (skip - (bne + 2)) & 0xFF
    code[bne2 + 1] = (skip - (bne2 + 2)) & 0xFF
    code += bytes([0x68, 0x28, 0x6B])  # PLA PLP RTL
    return bytes(code)


def main():
    rom = bytearray(ROM_PATH.read_bytes())
    if rom[HOOK_POINT : HOOK_POINT + 4] != bytes([0x22, 0xD8, 0xF8, 0x80]):
        raise SystemExit("Hook point mismatch")

    alloc = ScatterAllocator(safe_pair_ids(rom))
    ids = encode_to_slots(LINE1, SLOT_L1, alloc) + encode_to_slots(LINE2, SLOT_L2, alloc)
    assert len(ids) == SLOT_TOTAL

    print(f"Patch SAFE: {SLOT_TOTAL} words @ $7F:65E2 ($0122..$015C)")
    print(f"  L1: {LINE1!r}")
    print(f"  L2: {LINE2!r}")
    print(f"  IDs: {' '.join(f'{v:04X}' for v in ids)}")
    print(f"  Font pairs: {alloc.count()}")

    for (cl, cr), cid in alloc.p2id.items():
        rom[char_id_to_rom(cid) : char_id_to_rom(cid) + 64] = make_pair_tile(cl, cr)

    hook = assemble_hook(ids)
    if hook.count(0xFF) == 0:
        for i, b in enumerate(hook):
            if rom[HOOK_ROM + i] != 0xFF and rom[HOOK_ROM + i] != hook[i]:
                pass  # allow overwrite of prior test hook
    rom[HOOK_ROM : HOOK_ROM + len(hook)] = hook
    rom[HOOK_POINT : HOOK_POINT + 4] = bytes([
        0x22, HOOK_ADDR & 0xFF, (HOOK_ADDR >> 8) & 0xFF, HOOK_BANK,
    ])

    cs = fix_checksum(rom)
    OUT_PATH.write_bytes(rom)
    print(f"Hook {len(hook)} bytes, checksum ${cs:04X}")
    print(f"Written: {OUT_PATH.name}")


if __name__ == "__main__":
    main()
