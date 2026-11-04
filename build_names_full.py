#!/usr/bin/env python3
"""Relocation of the WHOLE character/enemy name table (Nage Libre).

The game takes a SURNAME + a GIVEN NAME from ONE shared table of 24-bit
pointers in bank $81, into the kanji string pool at $87:8077..:
    $81:AF5B  full table (244 entries)
    $81:B087  = the SAME bytes, a "given names" window starting at entry 100
              (given[k] == surname[100+k]: repointing one changes the other)
In battle the HP box shows "[surname] [given name]".

The kanji strings sit in slots too short for romaji → we RELOCATE:
we write the romanised names (read from docs/names_translation.csv, column `en`)
into a large free area at $AF:9E8F, then repoint every entry of the table.
Each name gets a trailing SPACE (separator between surname and given name); the
extra space after a given name at the end of the box is harmless.

We ONLY touch the lines whose `en` is filled in. Entries 0..4 (the 5 main
characters) are left to build_character_names (birthday screen).

apply(rom, alloc) is called by build_full_translation.py (shared allocator).
"""
import csv
from pathlib import Path

from patch_prologue_v3 import JP_SPACE, encode_en

ROOT = Path(__file__).parent
CSV_PATH = ROOT / "docs" / "names_translation.csv"

NAME_TBL = 0x0AF5B        # $81:AF5B (file offset): the single shared table
N_ENTRIES = 244           # $81:B087 (given names) is only an internal window
SKIP_MAIN = 5             # entries 0..4 = main characters (build_character_names)

# Free pool $AF:9E8F .. $AF:FFFF (24945 bytes)
POOL_FILE = 0x179E8F
POOL_BANK = 0xAF
POOL_ADDR = 0x9E8F
POOL_END = 0x180000


def _load_en():
    """idx -> romaji (filled-in lines), snes_off -> idx, idx -> role."""
    en_by_idx, idx_by_off, role_by_idx = {}, {}, {}
    if not CSV_PATH.is_file():
        return en_by_idx, idx_by_off, role_by_idx
    with CSV_PATH.open(encoding="utf-8") as f:
        for r in csv.DictReader(f):
            idx = int(r["idx"])
            off = int(r["snes_off"], 16)
            idx_by_off[off] = idx
            role_by_idx[idx] = (r.get("role") or "").strip()
            en = (r.get("en") or "").strip()
            if en:
                en_by_idx[idx] = en
    return en_by_idx, idx_by_off, role_by_idx


NAME_BLOCK_START = 0x038077   # block of name strings in $87
NAME_BLOCK_END = 0x038697     # (followed by the message block, scanned normally)


def _name_block_keep_ids(rom, en_by_idx, idx_by_off):
    """IDs of the UNtranslated name entries (to KEEP referenced). The kanji
    of translated (relocated) names are left out → can be freed for the font."""
    keep, cur, start, i = set(), [], 0x8077, NAME_BLOCK_START
    while i < NAME_BLOCK_END:
        w = rom[i] | (rom[i + 1] << 8)
        i += 2
        if w == 0xFFFF:
            idx = idx_by_off.get(start)
            if idx is None or idx not in en_by_idx:
                keep.update(c for c in cur if c < 0x0800)
            cur, start = [], 0x8000 + (i - 0x038000)
        elif w < 0x0800:
            cur.append(w)
    return keep


def compute_free_pool(rom):
    """List of free font IDs (>=0x100), name-aware: kanji that only
    belong to translated names are made available. Call it on the
    original ROM (before the pointers are relocated)."""
    import build_combat_menu_translation as M
    from patch_prologue_v3 import find_safe_ids

    en_by_idx, idx_by_off, _role = _load_en()

    ref = set(M.SPECIAL_IDS)
    i = NAME_BLOCK_END                       # message block: full scan
    while i < M.TEXT_BLOCK_END:
        w = rom[i] | (rom[i + 1] << 8)
        if w != 0xFFFF and w < 0x0800:
            ref.add(w)
        i += 2
    ref |= M._reserved_prologue_ids()
    ref |= M._script_pointer_ids(rom)
    ref |= _name_block_keep_ids(rom, en_by_idx, idx_by_off)

    return [cid for cid in find_safe_ids(rom)
            if cid >= 0x0100
            and not (0x0500 <= cid < 0x0570)
            and cid not in ref and (cid + 1) not in ref and (cid - 1) not in ref]


def _ptr_target(rom, tbl_file, e):
    a = tbl_file + e * 3
    return rom[a] | (rom[a + 1] << 8), rom[a + 2]


def _write_ptr(rom, tbl_file, e, bank, addr):
    a = tbl_file + e * 3
    rom[a] = addr & 0xFF
    rom[a + 1] = (addr >> 8) & 0xFF
    rom[a + 2] = bank & 0xFF


# Patch of the opponent HUD routine @ $81:C0B0 (0x00C0B0):
# Original: loads $13D8,X (surname) then $13D7,X (given name).
# Swapped: loads $13D7,X (given name) then $13D8,X (surname initial).
OPPONENT_HUD_PATCH_1 = 0x00C0B5   # BD D8 13 -> BD D7 13
OPPONENT_HUD_PATCH_2 = 0x00C0BE   # BD D7 13 -> BD D8 13


def apply(rom: bytearray, alloc):
    """Relocates the filled-in names and repoints the shared table. Returns the number
    of entries relocated (and the number of unique strings written to the pool)."""
    en_by_idx, idx_by_off, role_by_idx = _load_en()
    if not en_by_idx:
        return 0, 0

    # Swap the display order in the opponent battle HUD (given name, then surname initial)
    rom[OPPONENT_HUD_PATCH_1:OPPONENT_HUD_PATCH_1 + 3] = bytes([0xBD, 0xD7, 0x13])
    rom[OPPONENT_HUD_PATCH_2:OPPONENT_HUD_PATCH_2 + 3] = bytes([0xBD, 0xD8, 0x13])

    cursor = POOL_FILE
    cache = {}  # tuple(ids) -> 16-bit addr

    def intern(ids):
        nonlocal cursor
        key = tuple(ids)
        if key in cache:
            return cache[key]
        addr = POOL_ADDR + (cursor - POOL_FILE)
        need = len(ids) * 2
        if cursor + need > POOL_END:
            raise SystemExit("Name pool $AF:9E8F overflow.")
        for j, cid in enumerate(ids):
            rom[cursor + j * 2] = cid & 0xFF
            rom[cursor + j * 2 + 1] = (cid >> 8) & 0xFF
        cursor += need
        cache[key] = addr
        return addr

    def _ends_with_space(ids):
        last = ids[-1]
        if last == JP_SPACE:
            return True
        pair = alloc.id2p.get(last)        # tile (left, right)
        return bool(pair) and pair[1] == ' '

    def encode(en, trailing_space):
        ids = encode_en(en, alloc)
        while len(ids) > 1 and ids[-1] == JP_SPACE:
            ids.pop()
        # given name -> initial separator: a single space (names of
        # odd length already have an implicit one through the "X␣" tile).
        if trailing_space and not _ends_with_space(ids):
            ids = ids + [JP_SPACE]
        return ids + [0xFFFF]

    n_entries = 0
    for e in range(SKIP_MAIN, N_ENTRIES):
        addr16, bank = _ptr_target(rom, NAME_TBL, e)
        idx = idx_by_off.get(addr16)
        if idx is None or idx not in en_by_idx:
            continue
        raw_name = en_by_idx[idx]
        role = role_by_idx.get(idx)
        if role == "surname":
            # Surname initial followed by a period: "N." (one 16x16 tile)
            text = f"{raw_name[0].upper()}."
            a = intern(encode(text, trailing_space=False))
        else:
            # Given name: max 7 characters so that given name + " N." <= 10 characters
            if idx < 227 and len(raw_name) > 7:
                text = raw_name[:7]
            else:
                text = raw_name
            # trailing_space=True ensures a space separates the given name from the initial in the HUD
            a = intern(encode(text, trailing_space=True))
        _write_ptr(rom, NAME_TBL, e, POOL_BANK, a)
        n_entries += 1

    return n_entries, len(cache)
