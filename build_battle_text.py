#!/usr/bin/env python3
"""
Messages de combat (Nage Libre) : phrases anglaises assemblées dans le bon ordre.

Le journal de combat (boîte du bas, 28 colonnes : col 2..29, 2 rangées $15/$17)
est assemblé à l'exécution par les routines $81:98A4..$81:9D14 et $83:90E0..$83:9307 :
    [nom] + fragment + [nombre] + fragment
Chaque fragment est chargé par un motif fixe
    LDA #lo / STA $09 / LDA #hi / STA $0A / LDA #bank / STA $0B ; JSL $80:F4A7
On REPOINTE chaque site vers un fragment anglais propre à ce site (encodé en
demi-chasse 8x16, cf. build_scene_injection.encode_hw), placé en $BF:8000+.
Les fragments ne sont donc plus limités à la taille des slots japonais, et deux
sites qui partageaient une particule (は = « takes » / « gains » / « recovers »)
reçoivent chacun leur propre texte.

Noms dans les messages : la routine $81:9D19 (messages + fiche de statut $81:C0B0)
lit le tableau partagé $81:AF5B, encodé en paires 16x16 avec une espace finale
variable selon la parité. On lui donne un tableau PARALLÈLE en demi-chasse
(prénom sans espace finale, nom de famille = « ␣X. »), d'où un espacement exact.
Le HUD de PV ($81:BA82, copie brute de tuiles 16x16) garde le tableau en paires.

HUD de PV : $81:BA82 affiche le nom d'index X puis celui d'index Y. Les appelants
$81:873D / $81:8746 chargeaient X = nom de famille -> « K.Yui ». On échange les
deux chargements -> « Yui K. », « Shizuko N. ».

apply(rom) est appelé par build_full_translation.py (après NF.apply / N.apply).
"""
import struct

import build_character_names as N
import build_names_full as NF
from build_scene_injection import encode_hw

POOL_BANK = 0xBF
POOL_FILE = 0x1F8000           # $BF:8000
POOL_END = 0x200000

MSG_COLS = 28                  # largeur utile de la boîte du bas (col 2..29)

# (site SNES du « LDA #lo », cible JP d'origine, texte anglais)
# Lignes types (nom <= 7 lettres, nombre <= 3 chiffres) :
#   « Shizuko attacks! Gem bonus! »   « Shizuko takes 12 damage!! »
#   « Yui gains 3 DEF!! »             « Yui recovers 8 HP!! »
SITES = [
    # --- attaque / super coup ---
    (0x8198AF, 0x8786DF, " attacks!"),
    (0x8198D5, 0x878897, "'s special move!!"),
    # --- divers ---
    (0x8198F8, 0x878731, "Changing outfits..."),
    (0x81991B, 0x878749, "Run for it!!"),
    (0x81993E, 0x8787B3, "Don't run! Wait!!"),
    # --- dégâts (joueur -> adversaire, adversaire -> joueur) ---
    (0x819979, 0x878789, " Gem bonus!"),
    (0x81999B, 0x8786E9, " takes "),
    (0x8199B8, 0x8786ED, " damage!!"),
    (0x8199D6, 0x878797, "It did no damage!!"),
    (0x819A11, 0x878789, " Gem bonus!"),
    (0x819A33, 0x8786E9, " takes "),
    (0x819A50, 0x8786ED, " damage!!"),
    (0x819A6E, 0x878797, "It did no damage!!"),
    # --- défense ---
    (0x819A99, 0x878879, "Gem bonus!"),
    (0x819ABB, 0x8786E9, " gains "),
    (0x819AD8, 0x878705, " DEF!!"),
    (0x819B03, 0x878879, "Gem bonus!"),
    (0x819B25, 0x8786E9, " gains "),
    (0x819B42, 0x878705, " DEF!!"),
    # --- soin ---
    (0x819B6D, 0x878879, "Gem bonus!"),
    (0x819B8F, 0x8786E9, " recovers "),
    (0x819BAC, 0x8786FB, " HP!!"),
    (0x819BD7, 0x878879, "Gem bonus!"),
    (0x819BF9, 0x8786E9, " recovers "),
    (0x819C16, 0x8786FB, " HP!!"),
    # --- fuite ---
    (0x819C41, 0x87876F, "...barely got away..."),
    (0x819C55, 0x878755, "...got caught!!"),
    (0x819C80, 0x8787D5, "...she got away."),
    (0x819C94, 0x8787C7, "...caught up to her!"),
    # --- victoire : « [nom] is defeated!! » / « [N]0 Gold earned!! » ---
    (0x819CCB, 0x8787EB, " is defeated!!"),
    (0x819CFE, 0x8787F7, " Gold earned!!"),
    # --- nom inconnu ---
    (0x81BFD3, 0x8786D9, "??"),
    (0x81C118, 0x8786D9, "??"),
    # --- montée de stats (col 8) : « [stat] up by [N]!! » ---
    (0x8390E8, 0x878819, "HP up by "),
    (0x839105, 0x87880D, "!!"),
    (0x839138, 0x878821, "Power up by "),
    (0x839155, 0x87880D, "!!"),
    (0x839188, 0x878829, "Defense up by "),
    (0x8391A5, 0x87880D, "!!"),
    (0x8391D8, 0x87883D, "Speed up by "),
    (0x8391F5, 0x87880D, "!!"),
    (0x839228, 0x878833, "Spirit up by "),
    (0x839245, 0x87880D, "!!"),
    (0x83927A, 0x878847, "Level up to "),
    (0x839297, 0x87886B, "!!"),
    # --- club débloqué : « [club] » puis, rangée suivante col 5 ---
    (0x8392D3, 0x878851, ""),
    (0x8392F8, 0x878855, "is now selectable!!"),
]

# HUD de PV : (offset fichier, octets d'origine, octets patchés)
HUD_SWAPS = [
    (0x00873D, bytes.fromhex("ac8410ae8610"), bytes.fromhex("ac8610ae8410")),  # joueur
    (0x008746, bytes.fromhex("ac9c10ae9e10"), bytes.fromhex("ac9e10ae9c10")),  # adversaire
]

# $81:9D19 : LDA $81AF58,X / LDA $81AF59,X / LDA $81AF5A,X (index 1-based * 3)
NAME_LOOKUP_OPERANDS = (0x009D38, 0x009D3E, 0x009D44)


def lorom(snes):
    return ((snes >> 16) & 0x7F) * 0x8000 + (snes & 0x7FFF)


def _hw_names(rom):
    """Tableau parallèle (244 entrées) : textes demi-chasse pour $81:9D19.
    None = garder le pointeur d'origine (entrée non traduite)."""
    en_by_idx, idx_by_off, role_by_idx = NF._load_en()
    out = [None] * NF.N_ENTRIES
    for e in range(NF.N_ENTRIES):
        addr16, _bank = NF._ptr_target(rom, NF.NAME_TBL, e)
        idx = idx_by_off.get(addr16)
        if idx is None or idx not in en_by_idx:
            continue
        name = en_by_idx[idx]
        if role_by_idx.get(idx) == "surname":
            out[e] = f" {name[0].upper()}."
        elif idx < 227:
            out[e] = name[:7]          # même troncature que le HUD (NF.apply)
    for i, (given, surname_init) in enumerate(N.MAIN_PLAYERS):
        out[i] = " " + surname_init.strip()
        out[100 + i] = given
    return out


def apply(rom: bytearray, jp_rom: bytes):
    """Repointe les fragments de combat et la recherche de noms des messages.
    `jp_rom` = ROM d'origine (lecture du tableau de noms avant relocalisation)."""
    cursor = POOL_FILE
    cache = {}

    def intern(ids):
        nonlocal cursor
        key = tuple(ids)
        if key not in cache:
            if cursor + 2 * len(ids) > POOL_END:
                raise SystemExit("Dépassement de la zone texte de combat $BF.")
            for j, cid in enumerate(ids):
                struct.pack_into("<H", rom, cursor + 2 * j, cid)
            cache[key] = 0x8000 + (cursor - POOL_FILE)
            cursor += 2 * len(ids)
        return cache[key]

    # 1) Tableau de noms parallèle en tête de zone (3 o/entrée)
    table_file = cursor
    cursor += 3 * NF.N_ENTRIES
    names = _hw_names(jp_rom)
    for e, text in enumerate(names):
        o = NF.NAME_TBL + 3 * e
        if text is None:
            ptr = rom[o:o + 3]                     # pointeur courant (relocalisé ou JP)
        else:
            a = intern(encode_hw(text) + [0xFFFF])
            ptr = bytes([a & 0xFF, a >> 8, POOL_BANK])
        rom[table_file + 3 * e:table_file + 3 * e + 3] = ptr
    base = 0x8000 + (table_file - POOL_FILE) - 3   # index 1-based
    for k, o in enumerate(NAME_LOOKUP_OPERANDS):
        if rom[o - 1] != 0xBF or rom[o:o + 3] != bytes([0x58 + k, 0xAF, 0x81]):
            raise SystemExit(f"$81:9D19 inattendu à 0x{o:06X}")
        a = base + k
        rom[o:o + 3] = bytes([a & 0xFF, a >> 8, POOL_BANK])

    # 2) Fragments : un pointeur par site
    for site, jp_target, text in SITES:
        o = lorom(site)
        lo, hi, bk = jp_target & 0xFF, (jp_target >> 8) & 0xFF, jp_target >> 16
        expect = bytes([0xA9, lo, 0x85, 0x09, 0xA9, hi, 0x85, 0x0A, 0xA9, bk, 0x85, 0x0B])
        if rom[o:o + 12] != expect:
            raise SystemExit(f"Site de message inattendu à ${site:06X}")
        a = intern(encode_hw(text) + [0xFFFF])
        rom[o + 1] = a & 0xFF
        rom[o + 5] = a >> 8
        rom[o + 9] = POOL_BANK

    # 3) HUD de PV : prénom puis initiale
    for off, old, new in HUD_SWAPS:
        if rom[off:off + len(old)] != old:
            raise SystemExit(f"HUD de PV inattendu à 0x{off:06X}")
        rom[off:off + len(new)] = new

    longest = max(len(t) for t in names if t and not t.startswith(" "))
    return {"sites": len(SITES), "strings": len(cache), "bytes": cursor - POOL_FILE,
            "longest_name": longest}
