#!/usr/bin/env python3
"""Relocalisation de TOUTE la table de noms de personnages/ennemis (Nage Libre).

Le jeu tire un NOM DE FAMILLE + un PRÉNOM d'UN SEUL tableau de pointeurs 24-bit
partagé en banque $81, vers le pool de chaînes kanji en $87:8077.. :
    $81:AF5B  tableau complet (244 entrées)
    $81:B087  = MÊMES octets, fenêtre « prénoms » à partir de l'entrée 100
              (given[k] == surname[100+k] : repointer l'un modifie l'autre)
En combat la boîte de PV affiche « [nom de famille] [prénom] ».

Les chaînes kanji sont dans des slots trop courts pour du romaji → on RELOCALISE :
on écrit les noms romanisés (lus depuis docs/names_translation.csv, colonne `en`)
dans une grande zone libre $AF:9E8F, puis on repointe chaque entrée du tableau.
Chaque nom reçoit une ESPACE finale (séparateur entre nom et prénom) ; l'espace
en trop d'un prénom en fin de boîte est inoffensive.

On ne touche QUE les lignes dont `en` est rempli. Les entrées 0..4 (5 persos
principaux) sont laissées à build_character_names (écran anniversaire).

apply(rom, alloc) est appelé par build_full_translation.py (allocateur partagé).
"""
import csv
from pathlib import Path

from patch_prologue_v3 import JP_SPACE, encode_en

ROOT = Path(__file__).parent
CSV_PATH = ROOT / "docs" / "names_translation.csv"

NAME_TBL = 0x0AF5B        # $81:AF5B (offset fichier) — tableau unique partagé
N_ENTRIES = 244           # $81:B087 (prénoms) n'est qu'une fenêtre interne
SKIP_MAIN = 5             # entrées 0..4 = persos principaux (build_character_names)

# Pool libre $AF:9E8F .. $AF:FFFF (24945 o)
POOL_FILE = 0x179E8F
POOL_BANK = 0xAF
POOL_ADDR = 0x9E8F
POOL_END = 0x180000


def _load_en():
    """idx -> romaji (lignes remplies), snes_off -> idx, idx -> role."""
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


NAME_BLOCK_START = 0x038077   # bloc de chaînes de noms en $87
NAME_BLOCK_END = 0x038697     # (suivi du bloc messages, scanné normalement)


def _name_block_keep_ids(rom, en_by_idx, idx_by_off):
    """IDs des entrées de noms NON traduites (à GARDER référencées). Les kanji
    des noms traduits (relocalisés) sont omis → libérables pour la police."""
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
    """Liste d'IDs de police libres (>=0x100), consciente des noms : les kanji
    n'appartenant qu'à des noms traduits sont rendus disponibles. À appeler sur la
    ROM d'origine (avant relocalisation des pointeurs)."""
    import build_combat_menu_translation as M
    from patch_prologue_v3 import find_safe_ids

    en_by_idx, idx_by_off, _role = _load_en()

    ref = set(M.SPECIAL_IDS)
    i = NAME_BLOCK_END                       # bloc messages : scan complet
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


# Patch de la routine HUD adverse @ $81:C0B0 (0x00C0B0) :
# D'origine : charge $13D8,X (Nom de famille) puis $13D7,X (Prénom).
# Inversé : charge $13D7,X (Prénom) puis $13D8,X (Initiale nom de famille).
OPPONENT_HUD_PATCH_1 = 0x00C0B5   # BD D8 13 -> BD D7 13
OPPONENT_HUD_PATCH_2 = 0x00C0BE   # BD D7 13 -> BD D8 13


def apply(rom: bytearray, alloc):
    """Relocalise les noms remplis et repointe le tableau partagé. Renvoie le nb
    d'entrées relocalisées (et le nb de chaînes uniques écrites dans le pool)."""
    en_by_idx, idx_by_off, role_by_idx = _load_en()
    if not en_by_idx:
        return 0, 0

    # Inverse l'ordre d'affichage dans le HUD de combat adverse (Prénom puis Initiale Nom)
    rom[OPPONENT_HUD_PATCH_1:OPPONENT_HUD_PATCH_1 + 3] = bytes([0xBD, 0xD7, 0x13])
    rom[OPPONENT_HUD_PATCH_2:OPPONENT_HUD_PATCH_2 + 3] = bytes([0xBD, 0xD8, 0x13])

    cursor = POOL_FILE
    cache = {}  # tuple(ids) -> addr 16-bit

    def intern(ids):
        nonlocal cursor
        key = tuple(ids)
        if key in cache:
            return cache[key]
        addr = POOL_ADDR + (cursor - POOL_FILE)
        need = len(ids) * 2
        if cursor + need > POOL_END:
            raise SystemExit("Dépassement du pool de noms $AF:9E8F.")
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
        pair = alloc.id2p.get(last)        # tuile (gauche, droite)
        return bool(pair) and pair[1] == ' '

    def encode(en, trailing_space):
        ids = encode_en(en, alloc)
        while len(ids) > 1 and ids[-1] == JP_SPACE:
            ids.pop()
        # séparateur prénom -> initiale : une seule espace (les noms de
        # longueur impaire en ont déjà une implicite via la tuile « X␣ »).
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
            # Initiale du nom de famille suivie d'un point : "N." (1 tuile 16x16)
            text = f"{raw_name[0].upper()}."
            a = intern(encode(text, trailing_space=False))
        else:
            # Prénom : max 7 caractères pour garantir que Prénom + " N." <= 10 caractères
            if idx < 227 and len(raw_name) > 7:
                text = raw_name[:7]
            else:
                text = raw_name
            # trailing_space=True assure qu'une espace sépare le prénom de l'initiale dans le HUD
            a = intern(encode(text, trailing_space=True))
        _write_ptr(rom, NAME_TBL, e, POOL_BANK, a)
        n_entries += 1

    return n_entries, len(cache)
