#!/usr/bin/env python3
"""
*In-place* reinsertion of the Nage Libre battle/menu strings (bank $87).

Unlike the prologue narration (compressed → WRAM, which needs a hook),
the interface/battle/system text is stored UNCOMPRESSED in bank $87, as
16-bit font IDs terminated by `FFFF`, read directly by `$80:F4A7`.

So we rewrite each English string *at its original ROM offset* (VWF pair
encoding, 2 letters per word, like the prologue) followed by an `FFFF`. The engine
stops at the `FFFF`, so as long as `english_words + 1 <= slot_words + 1` (i.e.
`english_words <= slot_words`) we never overflow into the neighbouring string.

Data: docs/combat_menu_translation.csv
    (file_off, snes, slot_words, category, jp_full, en)

Usage:
    python3 build_combat_menu_translation.py [--cat hub,menu,combat,...] [--all]
                                             [--base ROM] [--out ROM]
Default: the `hub` category only, base = clean JP ROM, output nl-menu-en.sfc
"""
import argparse
import csv
import struct
from pathlib import Path

from patch_prologue_v3 import (
    JP_SPACE,
    ScatterAllocator,
    char_id_to_rom,
    encode_en,
    fix_checksum,
    find_safe_ids,
    make_pair_tile,
)

ROOT = Path(__file__).parent
ROM_JP = ROOT / "Nage Libre - Seijaku no Suishin (Japan).sfc"
CSV_PATH = ROOT / "docs" / "combat_menu_translation.csv"

# Uncompressed text block of bank $87 (names, clubs, battle, menus, birthstones…)
TEXT_BLOCK_START = 0x038077
TEXT_BLOCK_END = 0x038C01

# Special IDs never to reallocate (shared font)
SPECIAL_IDS = {0x03FE, 0x03FF, 0x02AA, 0x02AB, 0x02E0, 0x02E1}


RESERVED_FILE = ROOT / "docs" / "reserved_font_ids.txt"


def _reserved_prologue_ids():
    """Glyph IDs used by the prologue (compressed script → WRAM).
    Frozen in docs/reserved_font_ids.txt (see the initial generation)."""
    ids = set()
    if RESERVED_FILE.is_file():
        for ln in RESERVED_FILE.read_text().splitlines():
            ln = ln.strip()
            if ln and not ln.startswith("#"):
                ids.add(int(ln, 16))
    return ids


def _script_pointer_ids(rom):
    """IDs of every UNCOMPRESSED text table pointed to by code
    (dump_all_scripts.find_all_script_pointers): protects the other menus/dialogue."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("das", ROOT / "dump_all_scripts.py")
    das = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(das)
    ids = set()
    for p in das.find_all_script_pointers(bytes(rom)):
        for line in das.read_script(bytes(rom), p["script_rom"]):
            for cid in line:
                if cid < 0x0800:
                    ids.add(cid)
    return ids


def referenced_ids(rom):
    """Every ID used by text the game displays, never to be rewritten:
    the uncompressed $87 block + special IDs + prologue glyphs (compressed) +
    every uncompressed text table."""
    ref = set(SPECIAL_IDS)
    i = TEXT_BLOCK_START
    while i < TEXT_BLOCK_END:
        w = rom[i] | (rom[i + 1] << 8)
        if w != 0xFFFF and w < 0x0800:
            ref.add(w)
        i += 2
    ref |= _reserved_prologue_ids()
    ref |= _script_pointer_ids(rom)
    return ref


def safe_ids(rom):
    """Free even IDs (>=0x100) that overwrite NO displayed glyph.

    A pair tile written at N (even) takes the 16x16 glyph at N, but its
    halves overlap the half-glyphs of the odd IDs N-1 and N+1. So we exclude
    N if N, N-1 or N+1 is referenced."""
    ref = referenced_ids(rom)
    return [cid for cid in find_safe_ids(rom)
            if cid >= 0x0100
            and cid not in ref and (cid + 1) not in ref and (cid - 1) not in ref]


def load_rows(categories, take_all):
    rows = []
    with CSV_PATH.open(encoding="utf-8") as f:
        for r in csv.DictReader(f):
            en = (r.get("en") or "")
            if not en.strip():
                continue
            # keep leading spaces (suffixes like " hits!!" after a name)
            en = en.rstrip("\n\r")
            if not take_all and r["category"] not in categories:
                continue
            rows.append({
                "off": int(r["file_off"], 16),
                "snes": r["snes"],
                "slot": int(r["slot_words"]),
                "cat": r["category"],
                "jp": r["jp_full"],
                "en": en,
            })
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cat", default="hub",
                    help="comma-separated categories (default: hub)")
    ap.add_argument("--all", action="store_true", help="every category")
    ap.add_argument("--base", default=str(ROM_JP), help="ROM de base")
    ap.add_argument("--out", default=str(ROOT / "nl-menu-en.sfc"))
    args = ap.parse_args()

    cats = set(c.strip() for c in args.cat.split(",") if c.strip())
    rom = bytearray(Path(args.base).read_bytes())
    rows = load_rows(cats, args.all)
    if not rows:
        raise SystemExit("No 'en' line for these categories.")

    alloc = ScatterAllocator(safe_ids(rom))

    # 1) encoding + size check (must fit in place)
    plan = []
    errors = []
    for r in rows:
        ids = encode_en(r["en"], alloc)
        while len(ids) > 1 and ids[-1] == JP_SPACE:
            ids.pop()
        if len(ids) > r["slot"]:
            errors.append(f"  {r['snes']} '{r['en']}' = {len(ids)} words > slot {r['slot']} "
                          f"(max {r['slot']*2} letters)  [{r['jp']}]")
            continue
        plan.append((r, ids + [0xFFFF]))
    if errors:
        raise SystemExit("Strings too long (rewrite them shorter in the CSV):\n"
                         + "\n".join(errors))

    # 2) pair glyphs
    for (cl, cr), cid in alloc.p2id.items():
        rom[char_id_to_rom(cid):char_id_to_rom(cid) + 64] = make_pair_tile(cl, cr)

    # 3) in-place rewrite
    for r, ids in plan:
        for i, cid in enumerate(ids):
            struct.pack_into("<H", rom, r["off"] + i * 2, cid)

    fix_checksum(rom)
    out = Path(args.out)
    out.write_bytes(rom)

    print(f"Written: {out.name}")
    print(f"  base: {Path(args.base).name}")
    print(f"  categories: {'ALL' if args.all else ', '.join(sorted(cats))}")
    print(f"  {len(plan)} string(s) reinserted, {alloc.count()} font pairs "
          f"(of {len(alloc.free)} available)")
    for r, ids in plan:
        print(f"    {r['snes']} {len(ids)-1}/{r['slot']} words  "
              f"{r['jp']!r} -> {r['en']!r}")


if __name__ == "__main__":
    main()
