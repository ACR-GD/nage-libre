#!/usr/bin/env python3
"""
Prologue screen 1 — English (v4 fix).

v3 black screen: hook used REP #$20 + RTL without PHP/PLP after F8D8.
The phase loop @ $83:8103 requires the same CPU flags F8D8 left in place.

This matches the working v1 hook frame (PHP/REP/PHA … PLA/PLP/RTL) and adds
a one-shot flag @ $7F:6710 to avoid re-patching on later decompress calls.

Output: nl-prologue-test-4.sfc
"""
from pathlib import Path

from patch_prologue_v3 import (
    ScatterAllocator,
    char_id_to_rom,
    encode_to_slots,
    find_safe_ids,
    fix_checksum,
    make_pair_tile,
)

ROM_PATH = Path(__file__).parent / "Nage Libre - Seijaku no Suishin (Japan).sfc"
OUT_PATH = Path(__file__).parent / "nl-prologue-test-4.sfc"

HOOK_ROM = 0x01F8E3
HOOK_POINT = 0x0180FF
HOOK_BANK = 0x83
HOOK_ADDR = 0xF8E3
MIN_FONT_ID = 0x0100  # same range as working v1 display

WRAM_BASE = 0x7F65E2
WRAM_FLAG = 0x7F6710
SLOT_L1 = 16
SLOT_L2 = 14

LINE1 = "In a distant world,"
LINE2 = "a voice echoes..."


def safe_pair_ids(rom):
    return [cid for cid in find_safe_ids(rom) if cid >= MIN_FONT_ID]


def assemble_hook(text_ids):
    code = bytearray()
    code += bytes([0x22, 0xD8, 0xF8, 0x80])  # JSL $80:F8D8
    code += bytes([0x08, 0xC2, 0x20, 0x48])  # PHP REP #$20 PHA

    code += bytes([0xAF, 0x10, 0x67, 0x7F])  # LDA.l $7F:6710
    bne_skip = len(code)
    code += bytes([0xD0, 0x00])                # BNE skip (already patched)

    code += bytes([0xAF, 0x02, 0x66, 0x7F])  # LDA.l $7F:6602
    code += bytes([0xC9, 0x5A, 0x07])
    bne_sig = len(code)
    code += bytes([0xD0, 0x00])

    code += bytes([0xAF, 0x04, 0x66, 0x7F])  # LDA.l $7F:6604
    code += bytes([0xC9, 0x2A, 0x00])
    bne_sig2 = len(code)
    code += bytes([0xD0, 0x00])

    for i, cid in enumerate(text_ids):
        addr = WRAM_BASE + i * 2
        code += bytes([0xA9, cid & 0xFF, (cid >> 8) & 0xFF])
        code += bytes([0x8F, addr & 0xFF, (addr >> 8) & 0xFF, (addr >> 16) & 0xFF])

    code += bytes([0xA9, 0x01, 0x00])
    code += bytes([0x8F, WRAM_FLAG & 0xFF, (WRAM_FLAG >> 8) & 0xFF, (WRAM_FLAG >> 16) & 0xFF])

    skip = len(code)
    code[bne_skip + 1] = (skip - (bne_skip + 2)) & 0xFF
    code[bne_sig + 1] = (skip - (bne_sig + 2)) & 0xFF
    code[bne_sig2 + 1] = (skip - (bne_sig2 + 2)) & 0xFF
    code += bytes([0x68, 0x28, 0x6B])  # PLA PLP RTL
    return bytes(code)


def main():
    if not ROM_PATH.is_file():
        raise SystemExit(f"Missing ROM: {ROM_PATH}")

    rom = bytearray(ROM_PATH.read_bytes())
    if rom[HOOK_POINT : HOOK_POINT + 4] != bytes([0x22, 0xD8, 0xF8, 0x80]):
        raise SystemExit("Hook point $83:80FF mismatch")

    alloc = ScatterAllocator(safe_pair_ids(rom))
    ids = encode_to_slots(LINE1, SLOT_L1, alloc) + encode_to_slots(LINE2, SLOT_L2, alloc)

    for (cl, cr), cid in alloc.p2id.items():
        rom[char_id_to_rom(cid) : char_id_to_rom(cid) + 64] = make_pair_tile(cl, cr)

    hook = assemble_hook(ids)
    rom[HOOK_ROM : HOOK_ROM + len(hook)] = hook
    rom[HOOK_POINT : HOOK_POINT + 4] = bytes([
        0x22, HOOK_ADDR & 0xFF, (HOOK_ADDR >> 8) & 0xFF, HOOK_BANK,
    ])

    fix_checksum(rom)
    OUT_PATH.write_bytes(rom)

    print(f"Written: {OUT_PATH.name}")
    print(f"  Hook: v1 frame + one-shot $7F:6710")
    print(f"  Fonts >= ${MIN_FONT_ID:04X}: {alloc.count()} pairs")
    print(f"  {LINE1!r} / {LINE2!r}")


if __name__ == "__main__":
    main()
