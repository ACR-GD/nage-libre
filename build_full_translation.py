#!/usr/bin/env python3
"""
UNIFIED Nage Libre builder: prologue + battle/menus in a single ROM.

Combines both systems with a **shared font allocator** (a single pool of
free IDs) to avoid any tile collision:

  1. Prologue (narration): compressed script, decompressed into WRAM `$7F:64C0`.
     We hook `$83:80FF`: after decompression, the English strings are copied
     (ROM table in bank $83) to their WRAM offset. (= build_prologue_*)

  2. Battle / menus / system: plain strings in bank `$87`, rewritten
     *in place*, terminated by `FFFF`. (= build_combat_menu_*)

ID pool: we take the strictest set (the menu's, which excludes EVERY glyph
referenced in the `$87` text block), which is also valid for the prologue.

Sources: docs/prologue_translation.csv  +  docs/combat_menu_translation.csv
Output:  nl-full-en.sfc
"""
import csv
import struct
from pathlib import Path

from patch_prologue_v3 import (
    JP_SPACE,
    ScatterAllocator,
    char_id_to_rom,
    encode_en,
    fix_checksum,
    make_pair_tile,
)
import build_prologue_translation as P
import build_combat_menu_translation as M
import build_combat_command_menu as CMD
import build_character_names as N
import build_names_full as NF
import build_club_names as CLUB
import build_scene_injection as SCENE
import build_battle_text as BT
import build_pager_menu as PG
import build_save_menu as SAVE

ROOT = Path(__file__).parent
ROM_JP = ROOT / "Nage Libre - Seijaku no Suishin (Japan).sfc"
OUT = ROOT / "nl-full-en.sfc"
# Scene lines too long for their box (to shorten in docs/scenes/)
OVERFLOW_CSV = ROOT / "docs" / "scene_overflow.csv"


def main():
    rom = bytearray(ROM_JP.read_bytes())
    if rom[P.HOOK_POINT:P.HOOK_POINT + 4] != bytes([0x22, 0xD8, 0xF8, 0x80]):
        raise SystemExit("Unexpected hook point $83:80FF — is this a clean JP ROM?")

    # Shared pool: free IDs not used by ANY glyph of the $87 text block.
    # "Name-aware" variant: the kanji of the names we relocate (romaji) are
    # freed for the font, which unlocks ~128 extra slots.
    alloc = ScatterAllocator(NF.compute_free_pool(rom))

    # === 2) MENU/BATTLE: encoding + size check (in place) ===
    # Ghosting: these screens redraw their lines at a FIXED position (scrolling
    # selection, battle log, buy/sell/swap…). A new value SHORTER than the
    # previous one leaves the old tiles in VRAM ->
    # "Buy a card[cter]", "Topaz Lazuli", "[lla] 部"… So we pad EVERY
    # string with spaces up to the width of its slot (spaces are blank tiles
    # that erase the leftovers), BEFORE the FFFF, which stays at its original
    # position. Safe: we never write past the end of the original string.
    menu = M.load_rows(set(), take_all=True)
    menu_plan, errors = [], []
    for r in menu:
        ids = encode_en(r["en"], alloc)
        while len(ids) > 1 and ids[-1] == JP_SPACE:
            ids.pop()
        if len(ids) > r["slot"]:
            errors.append(f"  {r['snes']} '{r['en']}' = {len(ids)} > slot {r['slot']}")
            continue
        ids = ids + [JP_SPACE] * (r["slot"] - len(ids))   # pad -> erases ghosting
        menu_plan.append((r, ids + [0xFFFF]))
    if errors:
        raise SystemExit("Menu strings too long:\n" + "\n".join(errors))

    # === 2b) Character NAMES (birthday screen): relocation ===
    names_written, slash_cid, slash_glyph = N.apply(rom, alloc)

    # === 2c) Enemy/character NAMES in BATTLE: full table relocation ===
    #   Reads docs/names_translation.csv (column `en`); only touches filled-in
    #   rows, skips the 5 main characters (handled in 2b). Repoints the shared
    #   table $81:AF5B (244 entries, given-name window included) to $AF:9E8F.
    nf_entries, nf_strings = NF.apply(rom, alloc)

    # === 2d) CLUB NAMES (selection screen): short labels in place ===
    #   Club selection reads its names through the table $87:E346 -> $87:85FF..,
    #   separate from $81:AF5B (battle, already relocated). So we rewrite short
    #   English labels in place in $87:85FF.. (see build_club_names).
    clubs_written = CLUB.apply(rom, alloc)

    # === 1) COMPRESSED SCENES ($7F:64C0): MULTI-SCENE injection at scale ===
    #   Hook at $83:80FF: A=scene_idx -> directory (expanded ROM $B0+) -> copies the
    #   scene's English strings. Bounded by n_ids + FFFF = no overflow.
    #   Called LAST: the scenes take whatever font budget is left.
    scene_stats = SCENE.apply(rom, alloc)

    # === 3) Write ALL the pair tiles (shared pool, once) ===
    for (cl, cr), cid in alloc.p2id.items():
        rom[char_id_to_rom(cid):char_id_to_rom(cid) + 64] = make_pair_tile(cl, cr)
    # dedicated 16×16 "/" glyph for the date (overwrites the pair generated for this ID)
    rom[char_id_to_rom(slash_cid):char_id_to_rom(slash_cid) + 64] = slash_glyph

    # === 5) Menu/battle: in-place rewrite in $87 ===
    for r, ids in menu_plan:
        for i, cid in enumerate(ids):
            struct.pack_into("<H", rom, r["off"] + i * 2, cid)

    # === 6) BATTLE COMMAND menu: runtime hook (bank $80) ===
    #   + PAGER windows (WHO / orders): $87 templates + a branch of the same hook
    pager = PG.apply(rom, ROM_JP.read_bytes())
    CMD.apply(rom, PG.hook_params())

    # === 6b) BATTLE messages: fragments repointed per site + half-width names ===
    #   "[name] takes [N] damage!!", "[name] gains [N] DEF!!"… (see build_battle_text)
    #   + HP HUD in Given-name Initial order.
    battle = BT.apply(rom, ROM_JP.read_bytes())

    # === 6c) SAVE screen: "2面" -> "St2" (half-width strings, see build_save_menu)
    SAVE.apply(rom)

    with OVERFLOW_CSV.open("w", encoding="utf-8", newline="") as f:
        wr = csv.writer(f)
        wr.writerow(["scene_idx_hex", "offset_hex", "cols", "max_rows", "rows", "en"])
        for sidx, off, cols, max_rows, n_rows, en in scene_stats.get("overflow", []):
            wr.writerow([f"{sidx:04X}", f"0x{off:04X}", cols, max_rows, n_rows, en])

    fix_checksum(rom)
    OUT.write_bytes(rom)

    print(f"Written: {OUT.name}  ({len(rom) // 1024} KB)")
    print(f"  scenes (multi): {scene_stats['scenes']} scenes / "
          f"{scene_stats['lines']} lines injected"
          + (f" ({scene_stats['truncated']} truncated)" if scene_stats['truncated'] else "")
          + (f" ({len(scene_stats['overflow'])} overflow their box -> {OVERFLOW_CSV.name})"
             if scene_stats['overflow'] else "")
          + f"  |  battle/menu: {len(menu_plan)} string(s)")
    print(f"  battle command menu: hook @ $80:{CMD.HOOK_SNES:04X} "
          f"({' / '.join(w for _, _, w in CMD.CMDS)})")
    print(f"  PAGER windows: {pager['labels']} ({pager['bytes']} bytes @ $BF:F000)")
    print(f"  character names: {len(names_written)} relocated @ $87:FA0C "
          f"({', '.join(n for n, _, _ in names_written)})")
    print(f"  battle names (shared table): {nf_entries} entry(ies) repointed, "
          f"{nf_strings} unique string(s) @ $AF:9E8F")
    print(f"  clubs (selection screen): {clubs_written} short labels @ $87:85FF..")
    print(f"  battle messages: {battle['sites']} sites repointed, {battle['strings']} "
          f"half-width strings ({battle['bytes']} bytes) @ $BF:8000, "
          f"longest given name {battle['longest_name']} chars")
    print(f"  shared font: {alloc.count()} unique pairs (of {len(alloc.free)} available)")
    print(f"  scenes: hook {scene_stats['hook']} bytes @ $83:{SCENE.HOOK_ADDR:04X}, "
          f"directory+data {scene_stats['bytes'] // 1024} KB @ $B0:8000+")


if __name__ == "__main__":
    main()
