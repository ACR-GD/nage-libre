#!/usr/bin/env python3
"""
Réinjection *sur place* des chaînes de combat/menu (banque $87) de Nage Libre.

Contrairement à la narration du prologue (compressée → WRAM, nécessite un hook),
le texte d'interface/combat/système est stocké EN CLAIR dans la banque $87, en
IDs de police 16-bit terminés par `FFFF`, lu directement par `$80:F4A7`.

On réécrit donc chaque chaîne anglaise *à son offset ROM d'origine* (encodage
paires VWF, 2 lettres/mot, comme le prologue) suivie d'un `FFFF`. Le moteur
s'arrête au `FFFF`, donc tant que `mots_anglais + 1 <= slot_words + 1` (c.-à-d.
`mots_anglais <= slot_words`) on ne déborde jamais sur la chaîne voisine.

Données : docs/combat_menu_translation.csv
    (file_off, snes, slot_words, category, jp_full, en)

Usage :
    python3 build_combat_menu_translation.py [--cat hub,menu,combat,...] [--all]
                                             [--base ROM] [--out ROM]
Par défaut : catégorie `hub` seule, base = ROM JP propre, sortie nl-menu-en.sfc
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

# Bloc de texte en clair de la banque $87 (noms, clubs, combat, menus, pierres…)
TEXT_BLOCK_START = 0x038077
TEXT_BLOCK_END = 0x038C01

# IDs spéciaux à ne jamais réallouer (police partagée)
SPECIAL_IDS = {0x03FE, 0x03FF, 0x02AA, 0x02AB, 0x02E0, 0x02E1}


RESERVED_FILE = ROOT / "docs" / "reserved_font_ids.txt"


def _reserved_prologue_ids():
    """IDs de glyphes utilisés par le prologue (script compressé → WRAM).
    Figés dans docs/reserved_font_ids.txt (cf. génération initiale)."""
    ids = set()
    if RESERVED_FILE.is_file():
        for ln in RESERVED_FILE.read_text().splitlines():
            ln = ln.strip()
            if ln and not ln.startswith("#"):
                ids.add(int(ln, 16))
    return ids


def _script_pointer_ids(rom):
    """IDs de toutes les tables de texte NON compressées pointées par du code
    (dump_all_scripts.find_all_script_pointers) — protège les autres menus/dialogues."""
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
    """Tous les IDs utilisés par un texte affiché du jeu, à ne jamais réécrire :
    bloc $87 en clair + IDs spéciaux + glyphes du prologue (compressé) +
    toutes les tables de texte non compressées."""
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
    """IDs pairs libres (>=0x100) n'écrasant AUCUN glyphe affiché.

    Une tuile de paire écrite en N (pair) occupe le glyphe 16x16 en N mais ses
    moitiés chevauchent les demi-glyphes des IDs impairs N-1 et N+1. On exclut
    donc N si N, N-1 ou N+1 est référencé."""
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
            # on préserve les espaces de tête (suffixes type " hits!!" après un nom)
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
                    help="catégories séparées par des virgules (défaut: hub)")
    ap.add_argument("--all", action="store_true", help="toutes les catégories")
    ap.add_argument("--base", default=str(ROM_JP), help="ROM de base")
    ap.add_argument("--out", default=str(ROOT / "nl-menu-en.sfc"))
    args = ap.parse_args()

    cats = set(c.strip() for c in args.cat.split(",") if c.strip())
    rom = bytearray(Path(args.base).read_bytes())
    rows = load_rows(cats, args.all)
    if not rows:
        raise SystemExit("Aucune ligne 'en' pour ces catégories.")

    alloc = ScatterAllocator(safe_ids(rom))

    # 1) encodage + validation de la taille (doit tenir sur place)
    plan = []
    errors = []
    for r in rows:
        ids = encode_en(r["en"], alloc)
        while len(ids) > 1 and ids[-1] == JP_SPACE:
            ids.pop()
        if len(ids) > r["slot"]:
            errors.append(f"  {r['snes']} '{r['en']}' = {len(ids)} mots > slot {r['slot']} "
                          f"(max {r['slot']*2} lettres)  [{r['jp']}]")
            continue
        plan.append((r, ids + [0xFFFF]))
    if errors:
        raise SystemExit("Chaînes trop longues (réécris-les plus court dans le CSV) :\n"
                         + "\n".join(errors))

    # 2) glyphes des paires
    for (cl, cr), cid in alloc.p2id.items():
        rom[char_id_to_rom(cid):char_id_to_rom(cid) + 64] = make_pair_tile(cl, cr)

    # 3) réécriture sur place
    for r, ids in plan:
        for i, cid in enumerate(ids):
            struct.pack_into("<H", rom, r["off"] + i * 2, cid)

    fix_checksum(rom)
    out = Path(args.out)
    out.write_bytes(rom)

    print(f"Écrit : {out.name}")
    print(f"  base : {Path(args.base).name}")
    print(f"  catégories : {'TOUTES' if args.all else ', '.join(sorted(cats))}")
    print(f"  {len(plan)} chaîne(s) réinjectée(s), {alloc.count()} paires de police "
          f"(sur {len(alloc.free)} dispo)")
    for r, ids in plan:
        print(f"    {r['snes']} {len(ids)-1}/{r['slot']} mots  "
              f"{r['jp']!r} -> {r['en']!r}")


if __name__ == "__main__":
    main()
