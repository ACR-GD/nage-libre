#!/usr/bin/env python3
"""
Builder UNIFIÉ Nage Libre : prologue + combat/menus dans une seule ROM.

Combine les deux systèmes avec un **allocateur de police partagé** (un seul pool
d'IDs libres) pour éviter toute collision de tuiles :

  1. Prologue (narration) — script compressé décompressé en WRAM `$7F:64C0`.
     On hooke `$83:80FF` : après la décompression, on recopie les chaînes
     anglaises (table ROM en banque $83) à leur offset WRAM. (= build_prologue_*)

  2. Combat / menus / système — chaînes en clair de la banque `$87`, réécrites
     *sur place*, terminées par `FFFF`. (= build_combat_menu_*)

Pool d'IDs : on prend le jeu le plus strict (celui du menu, qui exclut TOUS les
glyphes référencés dans le bloc texte `$87`), valable aussi pour le prologue.

Sources : docs/prologue_translation.csv  +  docs/combat_menu_translation.csv
Sortie   : nl-full-en.sfc
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

ROOT = Path(__file__).parent
ROM_JP = ROOT / "Nage Libre - Seijaku no Suishin (Japan).sfc"
OUT = ROOT / "nl-full-en.sfc"
# Lignes de scène trop longues pour leur boîte (à raccourcir dans docs/scenes/)
OVERFLOW_CSV = ROOT / "docs" / "scene_overflow.csv"


def main():
    rom = bytearray(ROM_JP.read_bytes())
    if rom[P.HOOK_POINT:P.HOOK_POINT + 4] != bytes([0x22, 0xD8, 0xF8, 0x80]):
        raise SystemExit("Point de hook $83:80FF inattendu — ROM JP propre ?")

    # Pool partagé : IDs libres ne servant à AUCUN glyphe du bloc texte $87.
    # Variante « name-aware » : les kanji des noms qu'on relocalise (romaji) sont
    # libérés pour la police, ce qui débloque ~128 slots supplémentaires.
    alloc = ScatterAllocator(NF.compute_free_pool(rom))

    # === 2) MENU/COMBAT : encodage + validation taille (sur place) ===
    # Rémanence : ces écrans redessinent leurs lignes à position FIXE (sélection
    # qui défile, journal de combat, achat/vente/échange…). Une nouvelle valeur
    # plus COURTE que la précédente laisse les tuiles d'avant en VRAM ->
    # « Buy a card[cter] », « Topaz Lazuli », « [lla] 部 »… On remplit donc TOUTE
    # chaîne d'espaces jusqu'à la largeur de son slot (les espaces sont des
    # tuiles vierges qui effacent le reliquat), AVANT le FFFF qui reste à sa
    # position d'origine. Sûr : on ne déborde jamais hors de la chaîne d'origine.
    menu = M.load_rows(set(), take_all=True)
    menu_plan, errors = [], []
    for r in menu:
        ids = encode_en(r["en"], alloc)
        while len(ids) > 1 and ids[-1] == JP_SPACE:
            ids.pop()
        if len(ids) > r["slot"]:
            errors.append(f"  {r['snes']} '{r['en']}' = {len(ids)} > slot {r['slot']}")
            continue
        ids = ids + [JP_SPACE] * (r["slot"] - len(ids))   # pad -> efface la rémanence
        menu_plan.append((r, ids + [0xFFFF]))
    if errors:
        raise SystemExit("Chaînes menu trop longues :\n" + "\n".join(errors))

    # === 2b) NOMS de personnages (écran anniversaire) : relocalisation ===
    names_written, slash_cid, slash_glyph = N.apply(rom, alloc)

    # === 2c) NOMS d'ennemis/persos en COMBAT : relocalisation table complète ===
    #   Lit docs/names_translation.csv (colonne `en`) ; ne touche que les lignes
    #   remplies, saute les 5 persos principaux (gérés en 2b). Repointe le tableau
    #   partagé $81:AF5B (244 entrées, fenêtre prénoms incluse) vers $AF:9E8F.
    nf_entries, nf_strings = NF.apply(rom, alloc)

    # === 2d) NOMS DE CLUBS (écran de sélection) : libellés courts sur place ===
    #   La sélection de club lit ses noms via la table $87:E346 -> $87:85FF.. ,
    #   distincte de $81:AF5B (combat, déjà relocalisée). On réécrit donc des
    #   libellés anglais courts sur place dans $87:85FF.. (cf. build_club_names).
    clubs_written = CLUB.apply(rom, alloc)

    # === 1) SCÈNES COMPRESSÉES ($7F:64C0) : injection MULTI-SCÈNES à l'échelle ===
    #   Hook à $83:80FF : A=scene_idx -> annuaire (ROM étendue $B0+) -> recopie des
    #   chaînes anglaises de la scène. Borne n_ids + FFFF = aucun débordement.
    #   Appelé EN DERNIER : les scènes prennent le budget de police restant.
    scene_stats = SCENE.apply(rom, alloc)

    # === 3) Écrire TOUTES les tuiles de paires (pool partagé, une seule fois) ===
    for (cl, cr), cid in alloc.p2id.items():
        rom[char_id_to_rom(cid):char_id_to_rom(cid) + 64] = make_pair_tile(cl, cr)
    # glyphe « / » 16×16 dédié à la date (écrase la paire générée pour cet ID)
    rom[char_id_to_rom(slash_cid):char_id_to_rom(slash_cid) + 64] = slash_glyph

    # === 5) Menu/combat : réécriture sur place en $87 ===
    for r, ids in menu_plan:
        for i, cid in enumerate(ids):
            struct.pack_into("<H", rom, r["off"] + i * 2, cid)

    # === 6) Menu de COMMANDE en combat : hook runtime (banque $80) ===
    CMD.apply(rom)

    # === 6b) Ligne de dégâts : « [nom]は[N]のダメージ » -> « [nom] [N] damage!! ».
    # La particule sujet は est une chaîne 1-mot à $87:86E9 (hors CSV) ; on la
    # remplace par une espace ($87:86EB est déjà FFFF).
    struct.pack_into("<H", rom, 0x0386E9, JP_SPACE)

    with OVERFLOW_CSV.open("w", encoding="utf-8", newline="") as f:
        wr = csv.writer(f)
        wr.writerow(["scene_idx_hex", "offset_hex", "cols", "max_rows", "rows", "en"])
        for sidx, off, cols, max_rows, n_rows, en in scene_stats.get("overflow", []):
            wr.writerow([f"{sidx:04X}", f"0x{off:04X}", cols, max_rows, n_rows, en])

    fix_checksum(rom)
    OUT.write_bytes(rom)

    print(f"Écrit : {OUT.name}  ({len(rom) // 1024} Ko)")
    print(f"  scènes (multi) : {scene_stats['scenes']} scènes / "
          f"{scene_stats['lines']} lignes injectées"
          + (f" ({scene_stats['truncated']} tronquées)" if scene_stats['truncated'] else "")
          + (f" ({len(scene_stats['overflow'])} débordent de la boîte -> {OVERFLOW_CSV.name})"
             if scene_stats['overflow'] else "")
          + f"  |  combat/menu : {len(menu_plan)} chaîne(s)")
    print(f"  menu commande combat : hook @ $80:{CMD.HOOK_SNES:04X} "
          f"({' / '.join(w for _, _, w in CMD.CMDS)})")
    print(f"  noms perso : {len(names_written)} relocalisés @ $87:FA0C "
          f"({', '.join(n for n, _, _ in names_written)})")
    print(f"  noms combat (tableau partagé) : {nf_entries} entrée(s) repointée(s), "
          f"{nf_strings} chaîne(s) uniques @ $AF:9E8F")
    print(f"  clubs (écran sélection) : {clubs_written} libellés courts @ $87:85FF..")
    print(f"  police partagée : {alloc.count()} paires uniques (sur {len(alloc.free)} dispo)")
    print(f"  scènes : hook {scene_stats['hook']} o @ $83:{SCENE.HOOK_ADDR:04X}, "
          f"annuaire+données {scene_stats['bytes'] // 1024} Ko @ $B0:8000+")


if __name__ == "__main__":
    main()
