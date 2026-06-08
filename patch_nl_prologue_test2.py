#!/usr/bin/env python3
"""
Prologue screen 1 — English (approach v2).

Changes vs patch_nl_prologue_en.py:
  - $83:80FF left vanilla (JSL $80:F8D8) — no intercept on every decompress
  - Patch runs only when phase dispatcher hits phase 1 (JSR $8383EE)
  - Signature 075A+002A @ $7F:6602 still required
  - Font pairs use safe IDs >= $0600 only (avoid low tile/system range)

Output: nl-prologue-test-2.sfc
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
OUT_PATH = Path(__file__).parent / "nl-prologue-test-2.sfc"

# JSR $83F8E3 @ $83:810A (was JSR $8383EE — phase 1 only)
PHASE1_CALL_ROM = 0x01810A
PHASE1_CALL_EXPECT = bytes([0x20, 0xEE, 0x83])  # JSR $8383EE

STUB_ROM = 0x01F8E3
STUB_ADDR = 0xF8E3
ORIG_PHASE1 = 0x8383EE

MIN_FONT_ID = 0x0600
WRAM_BASE = 0x7F65E2
SLOT_L1 = 16
SLOT_L2 = 14

LINE1 = "In a distant world,"
LINE2 = "a voice echoes..."


def font_pool(rom):
    safe = [cid for cid in find_safe_ids(rom) if cid >= MIN_FONT_ID]
    if len(safe) < 25:
        raise RuntimeError(f"Not enough font IDs >= ${MIN_FONT_ID:04X} ({len(safe)} found)")
    return safe


def assemble_stub(text_ids):
    """$83:F8E3 — patch WRAM if screen-1 signature, then JMP phase-1 handler."""
    code = bytearray()
    code += bytes([0xAF, 0x02, 0x66, 0x7F])  # LDA.l $7F:6602
    code += bytes([0xC9, 0x5A, 0x07])        # CMP #$075A
    bne_sig = len(code)
    code += bytes([0xD0, 0x00])
    code += bytes([0xAF, 0x04, 0x66, 0x7F])  # LDA.l $7F:6604
    code += bytes([0xC9, 0x2A, 0x00])        # CMP #$002A
    bne_sig2 = len(code)
    code += bytes([0xD0, 0x00])

    for i, cid in enumerate(text_ids):
        addr = WRAM_BASE + i * 2
        code += bytes([0xA9, cid & 0xFF, (cid >> 8) & 0xFF])
        code += bytes([0x8F, addr & 0xFF, (addr >> 8) & 0xFF, (addr >> 16) & 0xFF])

    skip = len(code)
    code[bne_sig + 1] = (skip - (bne_sig + 2)) & 0xFF
    code[bne_sig2 + 1] = (skip - (bne_sig2 + 2)) & 0xFF
    code += bytes([0x4C, ORIG_PHASE1 & 0xFF, (ORIG_PHASE1 >> 8) & 0xFF])  # JMP $8383EE
    return bytes(code)


def main():
    if not ROM_PATH.is_file():
        raise SystemExit(f"Missing ROM: {ROM_PATH}")

    rom = bytearray(ROM_PATH.read_bytes())

    if rom[PHASE1_CALL_ROM : PHASE1_CALL_ROM + 3] != PHASE1_CALL_EXPECT:
        raise SystemExit(
            f"Expected JSR $8383EE @ $83:810A, got {rom[PHASE1_CALL_ROM:PHASE1_CALL_ROM+3].hex()}"
        )

    # $83:80FF must remain vanilla decompress call
    if rom[0x0180FF : 0x0180FF + 4] != bytes([0x22, 0xD8, 0xF8, 0x80]):
        raise SystemExit("$83:80FF is not vanilla JSL $80:F8D8 — use a clean JP ROM")

    alloc = ScatterAllocator(font_pool(rom))
    ids = encode_to_slots(LINE1, SLOT_L1, alloc) + encode_to_slots(LINE2, SLOT_L2, alloc)
    assert len(ids) == SLOT_L1 + SLOT_L2

    for (cl, cr), cid in alloc.p2id.items():
        rom[char_id_to_rom(cid) : char_id_to_rom(cid) + 64] = make_pair_tile(cl, cr)

    stub = assemble_stub(ids)
    if len(stub) > 512:
        raise SystemExit(f"Stub too large ({len(stub)} bytes)")

    rom[STUB_ROM : STUB_ROM + len(stub)] = stub
    rom[PHASE1_CALL_ROM : PHASE1_CALL_ROM + 3] = bytes([
        0x20, STUB_ADDR & 0xFF, (STUB_ADDR >> 8) & 0xFF,
    ])

    fix_checksum(rom)
    OUT_PATH.write_bytes(rom)

    print(f"Written: {OUT_PATH.name}")
    print(f"  Decompress $83:80FF: vanilla (unchanged)")
    print(f"  Hook: $83:810A JSR $83:{STUB_ADDR:04X} (phase 1 only)")
    print(f"  L1: {LINE1!r}")
    print(f"  L2: {LINE2!r}")
    print(f"  Font IDs >= ${MIN_FONT_ID:04X}: {alloc.count()} pairs")
    print(f"  Stub: {len(stub)} bytes")


if __name__ == "__main__":
    main()
