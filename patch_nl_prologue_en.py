#!/usr/bin/env python3
"""
Patch prologue screen 1 (starfield) — English opening lines.

Source: Nage Libre - Seijaku no Suishin (Japan).sfc
Output: nl-prologue-en.sfc

Hook $83:80FF → $83:F8E3: JSL $80:F8D8, then replace 30 tilemap words at
$7F:65E2 when signature 075A+002A @ $7F:6602 (screen 1 only).
Also clears row $0222 ($7F:66E2) so preloaded screen-2 JP text cannot leak
through the 7 phase handlers (fixes end-of-prologue hang).

See docs/prologue_text_engine.md
"""
from pathlib import Path

from patch_prologue_v3 import (
    JP_SPACE,
    ScatterAllocator,
    char_id_to_rom,
    encode_to_slots,
    find_safe_ids,
    fix_checksum,
    make_pair_tile,
)

ROM_PATH = Path(__file__).parent / "Nage Libre - Seijaku no Suishin (Japan).sfc"
OUT_PATH = Path(__file__).parent / "nl-prologue-en.sfc"

HOOK_ROM = 0x01F8E3
HOOK_POINT = 0x0180FF
HOOK_BANK = 0x83
HOOK_ADDR = 0xF8E3
HOOK_ADDR_SUB = 0xF950

MIN_FONT_ID = 0x0100
WRAM_BASE = 0x7F65E2
WRAM_TILEMAP = 0x7F64C0
ROW3_OFFSET = 0x0222
ROW3_SLOTS = 16
SLOT_L1 = 16
SLOT_L2 = 14

# Two leading spaces on L1 — first visible cell is off-screen without them.
LINE1 = "  In a distant world,"
LINE2 = " a voice echoes..."


def safe_pair_ids(rom):
    return [cid for cid in find_safe_ids(rom) if cid >= MIN_FONT_ID]


def _exit_rts():
    return bytes([0x28, 0x60])  # PLP RTS


def _append_clear_row3(code: bytearray):
    """16× JP_SPACE @ $7F:64C0 + $0222 — wipe screen-2 preload row."""
    code += bytes([0xA2, ROW3_OFFSET & 0xFF, (ROW3_OFFSET >> 8) & 0xFF])
    code += bytes([0xA9, JP_SPACE & 0xFF, (JP_SPACE >> 8) & 0xFF])
    loop = len(code)
    code += bytes([0x9F, WRAM_TILEMAP & 0xFF, (WRAM_TILEMAP >> 8) & 0xFF, (WRAM_TILEMAP >> 16) & 0xFF])
    code += bytes([0xE8, 0xE8])
    end_x = ROW3_OFFSET + ROW3_SLOTS * 2
    code += bytes([0xE0, end_x & 0xFF, (end_x >> 8) & 0xFF])
    bcc = len(code)
    code += bytes([0x90, 0x00])
    code[bcc + 1] = (loop - (bcc + 2)) & 0xFF


def assemble_patch_sub(text_ids):
    code = bytearray()
    code += bytes([0x08, 0xC2, 0x20])  # PHP REP #$20

    code += bytes([0xAF, 0x02, 0x66, 0x7F])
    code += bytes([0xC9, 0x5A, 0x07])
    beq_sig2 = len(code)
    code += bytes([0xF0, 0x00])
    code += _exit_rts()

    sig2 = len(code)
    code[beq_sig2 + 1] = sig2 - (beq_sig2 + 2)

    code += bytes([0xAF, 0x04, 0x66, 0x7F])
    code += bytes([0xC9, 0x2A, 0x00])
    beq_patch = len(code)
    code += bytes([0xF0, 0x00])
    code += _exit_rts()

    patch = len(code)
    code[beq_patch + 1] = patch - (beq_patch + 2)

    for i, cid in enumerate(text_ids):
        addr = WRAM_BASE + i * 2
        code += bytes([0xA9, cid & 0xFF, (cid >> 8) & 0xFF])
        code += bytes([0x8F, addr & 0xFF, (addr >> 8) & 0xFF, (addr >> 16) & 0xFF])

    _append_clear_row3(code)
    code += _exit_rts()
    return bytes(code)


def assemble_hook():
    code = bytearray()
    code += bytes([0x22, 0xD8, 0xF8, 0x80])
    code += bytes([0x20, HOOK_ADDR_SUB & 0xFF, (HOOK_ADDR_SUB >> 8) & 0xFF])
    code += bytes([0x6B])
    return bytes(code)


def main():
    if not ROM_PATH.is_file():
        raise SystemExit(f"Missing ROM: {ROM_PATH}")

    rom = bytearray(ROM_PATH.read_bytes())
    if rom[HOOK_POINT : HOOK_POINT + 4] != bytes([0x22, 0xD8, 0xF8, 0x80]):
        raise SystemExit("Hook point $83:80FF mismatch — not a clean JP ROM?")

    alloc = ScatterAllocator(safe_pair_ids(rom))
    ids = encode_to_slots(LINE1, SLOT_L1, alloc) + encode_to_slots(LINE2, SLOT_L2, alloc)
    assert len(ids) == SLOT_L1 + SLOT_L2

    for (cl, cr), cid in alloc.p2id.items():
        rom[char_id_to_rom(cid) : char_id_to_rom(cid) + 64] = make_pair_tile(cl, cr)

    hook = assemble_hook()
    sub = assemble_patch_sub(ids)
    sub_off = HOOK_ADDR_SUB - HOOK_ADDR
    rom[HOOK_ROM : HOOK_ROM + len(hook)] = hook
    rom[HOOK_ROM + sub_off : HOOK_ROM + sub_off + len(sub)] = sub
    rom[HOOK_POINT : HOOK_POINT + 4] = bytes([
        0x22, HOOK_ADDR & 0xFF, (HOOK_ADDR >> 8) & 0xFF, HOOK_BANK,
    ])

    fix_checksum(rom)
    OUT_PATH.write_bytes(rom)

    print(f"Written: {OUT_PATH.name}")
    print(f"  L1 ({SLOT_L1} slots): {LINE1!r}")
    print(f"  L2 ({SLOT_L2} slots): {LINE2!r}")
    print(f"  Font pairs: {alloc.count()}")
    print(f"  Hook: {len(hook)} B @ $83:F8E3, sub: {len(sub)} B @ $83:F950")
    print(f"  Clears {ROW3_SLOTS} words @ $7F:66E2 (row $0222 preload)")


if __name__ == "__main__":
    main()
