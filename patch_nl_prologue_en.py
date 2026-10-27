#!/usr/bin/env python3
"""
Patch prologue screen 1 (starfield) — English opening lines.

Insertion minimale (doc prologue_text_engine.md) :
  • 14 mots @ $7F:6602 seulement (flux texte JP, même longueur)
  • Ne pas toucher $7F:65E2 (rangée visible / bordures — remplie par les 7 phases)
  • Ne pas effacer row $0222 (preload écran 2 / transition fin prologue)

Le patch 30 mots @ $65E2 + clear $0222 provoquait le plantage en fin de prologue.

Output: nl-prologue-en.sfc
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
OUT_PATH = Path(__file__).parent / "nl-prologue-en.sfc"

HOOK_ROM = 0x01F8E3
HOOK_POINT = 0x0180FF
HOOK_BANK = 0x83
HOOK_ADDR = 0xF8E3
HOOK_ADDR_SUB = 0xF950

MIN_FONT_ID = 0x0100
WRAM_TEXT = 0x7F6602  # offset $0142 — 14 mots texte écran 1
SLOT_COUNT = 14

# 14 slots VWF ≈ même empreinte que 遠くの世界で……声が響く……
LINE = "In a distant world,a voice echoes"


def safe_pair_ids(rom):
    return [cid for cid in find_safe_ids(rom) if cid >= MIN_FONT_ID]


def _exit_rts():
    return bytes([0x28, 0x60])


def assemble_patch_sub(text_ids: list[int]) -> bytes:
    code = bytearray()
    code += bytes([0x08, 0xC2, 0x20])

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
        addr = WRAM_TEXT + i * 2
        code += bytes([0xA9, cid & 0xFF, (cid >> 8) & 0xFF])
        code += bytes([0x8F, addr & 0xFF, (addr >> 8) & 0xFF, (addr >> 16) & 0xFF])

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
    ids = encode_to_slots(LINE, SLOT_COUNT, alloc)
    assert len(ids) == SLOT_COUNT

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
    print(f"  {SLOT_COUNT} mots @ $7F:6602 uniquement (pas $65E2, pas clear $0222)")
    print(f"  Texte: {LINE!r}")
    print(f"  IDs: {' '.join(f'{v:04X}' for v in ids)}")
    print(f"  Font pairs: {alloc.count()}")
    print(f"  Hook: {len(hook)} B @ $83:F8E3, sub: {len(sub)} B @ $83:F950")


if __name__ == "__main__":
    main()
