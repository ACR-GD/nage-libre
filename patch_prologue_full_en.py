#!/usr/bin/env python3
"""
Prologue EN — nl-prologue-full-en.sfc

Écran 1 : hook décompression (patch_nl_prologue_erase_en.py)
UI anniversaire : table $87:8697 (#41–44, pierres #51–59)
Pierres : table $87:89C5 entrées 3–11 (FFFF) — PAS les offsets 8A51/61/71
  (ces adresses = noms JP des pierres, réutilisés par le prologue écran 2)

Écran 2 prologue : non patché en ROM (conflit avec pierres / heap partagé).
"""
from __future__ import annotations

import struct
from pathlib import Path

from patch_nl_prologue_en import (
    HOOK_ADDR,
    HOOK_ADDR_SUB,
    HOOK_BANK,
    HOOK_POINT,
    HOOK_ROM,
    LINE,
    SLOT_COUNT,
    assemble_hook,
    assemble_patch_sub,
    safe_pair_ids,
)
from patch_prologue_v3 import (
    ScatterAllocator,
    char_id_to_rom,
    encode_to_slots,
    fix_checksum,
    make_pair_tile,
)

ROM_PATH = Path(__file__).parent / "Nage Libre - Seijaku no Suishin (Japan).sfc"
OUT_PATH = Path(__file__).parent / "nl-prologue-full-en.sfc"

TABLE_8697 = 0x038697
TABLE_89C5 = 0x0389C5

# Entrées table $87:8697 (index = numéro d'entrée FFFF)
UI_8697: dict[int, str] = {
    41: "/",
    42: "  ",
    43: "Birthday?",
    44: "B-day OK?",
    51: "Garnet",
    52: "Amethyst",
    53: "Aqua",
    54: "Diamond",
    55: "Emerald",
    56: "Moonstone",
    57: "Ruby",
    58: "Agate",
    59: "Sapphire",
}

# Entrées 3–11 de la table $87:89C5 (écran anniversaire lit cette table)
STONES_89C5: dict[int, str] = {
    3: "Garnet",
    4: "Amethyst",
    5: "Aqua",
    6: "Diamond",
    7: "Emerald",
    8: "Moonstone",
    9: "Ruby",
    10: "Agate",
    11: "Sapphire",
    12: "Opal",
    13: "Topaz",
    14: "Lapis",
}


def _iter_ffff_entries(rom: bytearray, start: int, end: int):
    """Yield (entry_index, entry_start_offset, slot_count) for each FFFF string."""
    i = start
    entry = 0
    cur_start = start
    while i < end:
        w = rom[i] | (rom[i + 1] << 8)
        if w == 0xFFFF:
            n = (i - cur_start) // 2
            yield entry, cur_start, n
            entry += 1
            cur_start = i + 2
        i += 2


def patch_ffff_table(
    rom: bytearray,
    start: int,
    end: int,
    translations: dict[int, str],
    alloc: ScatterAllocator,
) -> None:
    for entry, off, slots in _iter_ffff_entries(rom, start, end):
        if entry not in translations:
            continue
        ids = encode_to_slots(translations[entry], slots, alloc)
        for j, cid in enumerate(ids):
            struct.pack_into("<H", rom, off + j * 2, cid)


def main() -> None:
    if not ROM_PATH.is_file():
        raise SystemExit(f"ROM introuvable: {ROM_PATH}")

    rom = bytearray(ROM_PATH.read_bytes())
    if rom[HOOK_POINT : HOOK_POINT + 4] != bytes([0x22, 0xD8, 0xF8, 0x80]):
        raise SystemExit("Point de hook $83:80FF invalide")

    alloc = ScatterAllocator(safe_pair_ids(rom))
    s1_ids = encode_to_slots(LINE, SLOT_COUNT, alloc)

    patch_ffff_table(rom, TABLE_8697, 0x038C01, UI_8697, alloc)
    patch_ffff_table(rom, TABLE_89C5, 0x038B00, STONES_89C5, alloc)

    for (cl, cr), cid in alloc.p2id.items():
        rom[char_id_to_rom(cid) : char_id_to_rom(cid) + 64] = make_pair_tile(cl, cr)

    hook = assemble_hook()
    sub = assemble_patch_sub(s1_ids)
    sub_off = HOOK_ADDR_SUB - HOOK_ADDR
    rom[HOOK_ROM : HOOK_ROM + len(hook)] = hook
    rom[HOOK_ROM + sub_off : HOOK_ROM + sub_off + len(sub)] = sub
    rom[HOOK_POINT : HOOK_POINT + 4] = bytes([
        0x22, HOOK_ADDR & 0xFF, (HOOK_ADDR >> 8) & 0xFF, HOOK_BANK,
    ])

    fix_checksum(rom)
    OUT_PATH.write_bytes(rom)

    print(f"Écrit: {OUT_PATH.name}")
    print(f"  Écran 1: {LINE!r} ({SLOT_COUNT} mots @ $6602)")
    print(f"  UI $8697: {len(UI_8697)} entrées")
    print(f"  Pierres $89C5: entrées {sorted(STONES_89C5)}")
    print(f"  Écran 2 prologue: non patché (heap partagé)")
    print(f"  Police: {alloc.count()} paires")


if __name__ == "__main__":
    main()
