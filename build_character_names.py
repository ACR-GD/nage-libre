#!/usr/bin/env python3
"""
Traduction des NOMS de personnages (Nage Libre).

Le moteur $80:F4A7 affiche les noms de personnages via les tables de pointeurs 24-bit :
    $81:AF5B  table NOMS DE FAMILLE  (entrées 0..4 = joueurs principaux)
    $81:B087  table PRÉNOMS          (entrées 100..104 = joueurs principaux)

En combat et sur l'écran d'anniversaire :
- Le HUD supérieur affiche le prénom puis l'initiale du nom de famille :
  "Ayaka S.", "Mai H.", "Yui K.", "Miki S.", "Ryoko A." (max 8 car., loge dans la boîte de 10).
- Les messages d'action en bas (ex. "Yui hits!!") appellent JSR $9D19 avec l'index de prénom
  (100 + char_idx). Les prénoms doivent donc être présents dans GIVEN_TBL ($81:B087).
- La table d'ordre à $87:DB2C (0x03DB2C) est inversée pour afficher Prénom puis Initiale Nom.

Personnages (ordre de la table) :
    0 桜井彩香  1 姫ノ木舞  2 霧島惟  3 静本美姫  4 葵嶺子
"""
from pathlib import Path

from patch_prologue_v3 import JP_SPACE, encode_en, _rows_to_2bpp

ROOT = Path(__file__).parent

# Tables de pointeurs 24-bit (offsets fichier)
SURNAME_TBL = 0x0AF5B          # $81:AF5B
GIVEN_TBL = 0x0B087            # $81:B087
N_CHARS = 5

# Table d'ordre d'affichage des noms (HUD combat joueur et écran d'anniversaire)
# Format d'origine : 01 65 02 66 03 67 04 68 05 69 (Nom, Prénom)
# Inversé :          65 01 66 02 67 03 68 04 69 05 (Prénom, Nom)
PLAYER_NAME_ORDER_FILE = 0x03DB2C
PLAYER_NAME_ORDER = bytes([0x65, 0x01, 0x66, 0x02, 0x67, 0x03, 0x68, 0x04, 0x69, 0x05])

# Zone libre banque $87 pour les chaînes relocalisées
DATA_FILE = 0x03FA0C           # $87:FA0C
DATA_BANK = 0x87
DATA_ADDR = 0xFA0C             # adresse 16-bit dans la banque
DATA_END = 0x03FFF0            # marge avant fin de banque

# Date d'anniversaire « N月 N日 » : chaînes mono-glyphe pointées par le code.
DATE_MONTH_FILE = 0x038965     # $87:8965  (月, ID 32C)
DATE_DAY_FILE = 0x038969       # $87:8969  (日, ID 2C8)

# Noms des 5 héroïnes : (Prénom, Initiale Nom de Famille)
# Pour Miki (longueur paire 4 car.), l'initiale prend une espace de tête " S." (2 tuiles).
# Pour Ayaka/Mai/Yui/Ryoko (longueurs impaires 3 ou 5 car.), la dernière tuile a déjà une espace
# intégrée, donc l'initiale est "S." / "H." / "K." / "A." (1 tuile).
MAIN_PLAYERS = [
    ("Ayaka", "S."),      # 桜井彩香  (Ay-ak-a␣ + S.  = Ayaka S., 4 tuiles)
    ("Mai", "H."),        # 姫ノ木舞  (Ma-i␣    + H.  = Mai H.,   3 tuiles)
    ("Yui", "K."),        # 霧島惟    (Yu-i␣    + K.  = Yui K.,   3 tuiles)
    ("Miki", " S."),      # 静本美姫  (Mi-ki    + ␣S-.␣ = Miki S., 4 tuiles)
    ("Ryoko", "A."),      # 葵嶺子    (Ry-ok-o␣ + A.  = Ryoko A., 4 tuiles)
]


def _write_ptr(rom, tbl_file, idx, bank, addr):
    a = tbl_file + idx * 3
    rom[a] = addr & 0xFF
    rom[a + 1] = (addr >> 8) & 0xFF
    rom[a + 2] = bank & 0xFF


def make_slash16():
    """Glyphe « / » 16×16 (2bpp) plein, pour le séparateur de date entre les
    gros chiffres. Diagonale bas-gauche → haut-droite, ~3px de large.
    Format de retour : 64 o = sous-tuiles lt, lb, rt, rb (cf. make_pair_tile)."""
    grid = [0] * 16                       # 16 lignes, bit15 = colonne 0 (gauche)
    for r in range(16):
        center = 15 - r                   # pente 1
        for dc in (-1, 0, 1):             # 3px de large
            c = center + dc
            if 0 <= c <= 15:
                grid[r] |= 1 << (15 - c)
    def sub(rows, hi):
        out = []
        for r in rows:
            out.append((grid[r] >> 8) & 0xFF if hi else grid[r] & 0xFF)
        return out
    lt = sub(range(0, 8), hi=True)        # haut-gauche
    lb = sub(range(8, 16), hi=True)       # bas-gauche
    rt = sub(range(0, 8), hi=False)       # haut-droite
    rb = sub(range(8, 16), hi=False)      # bas-droite
    return (_rows_to_2bpp(lt) + _rows_to_2bpp(lb)
            + _rows_to_2bpp(rt) + _rows_to_2bpp(rb))


def apply(rom: bytearray, alloc):
    """Encode les prénoms et initiales, écrit la table d'ordre et repointe GIVEN_TBL et SURNAME_TBL."""
    if len(MAIN_PLAYERS) != N_CHARS:
        raise SystemExit(f"MAIN_PLAYERS doit contenir {N_CHARS} entrées.")

    # 1. Inverse l'ordre d'affichage (Prénom d'abord, Initiale de nom ensuite)
    rom[PLAYER_NAME_ORDER_FILE:PLAYER_NAME_ORDER_FILE + len(PLAYER_NAME_ORDER)] = PLAYER_NAME_ORDER

    cursor = DATA_FILE
    written = []

    for i, (given, surname_init) in enumerate(MAIN_PLAYERS):
        # Encodage Prénom -> GIVEN_TBL ($81:B087)
        g_ids = encode_en(given, alloc)
        while len(g_ids) > 1 and g_ids[-1] == JP_SPACE:
            g_ids.pop()
        g_ids = g_ids + [0xFFFF]
        g_addr = DATA_ADDR + (cursor - DATA_FILE)
        if cursor + len(g_ids) * 2 > DATA_END:
            raise SystemExit("Dépassement zone libre $87:FA0C pour les noms.")
        for j, cid in enumerate(g_ids):
            rom[cursor + j * 2] = cid & 0xFF
            rom[cursor + j * 2 + 1] = (cid >> 8) & 0xFF
        cursor += len(g_ids) * 2
        _write_ptr(rom, GIVEN_TBL, i, DATA_BANK, g_addr)

        # Encodage Initiale Nom -> SURNAME_TBL ($81:AF5B)
        s_ids = encode_en(surname_init, alloc)
        while len(s_ids) > 1 and s_ids[-1] == JP_SPACE:
            s_ids.pop()
        s_ids = s_ids + [0xFFFF]
        s_addr = DATA_ADDR + (cursor - DATA_FILE)
        if cursor + len(s_ids) * 2 > DATA_END:
            raise SystemExit("Dépassement zone libre $87:FA0C pour les noms.")
        for j, cid in enumerate(s_ids):
            rom[cursor + j * 2] = cid & 0xFF
            rom[cursor + j * 2 + 1] = (cid >> 8) & 0xFF
        cursor += len(s_ids) * 2
        _write_ptr(rom, SURNAME_TBL, i, DATA_BANK, s_addr)

        written.append((f"{given} {surname_init.strip()}", g_addr, len(g_ids) + len(s_ids)))

    # Date « N月 N日 » → « N / N » : glyphe « / » 16×16 dédié dans la case du mois.
    slash_cid = alloc.get("/", "/")          # ID réservé (réécrit en glyphe 16×16)
    rom[DATE_MONTH_FILE] = slash_cid & 0xFF
    rom[DATE_MONTH_FILE + 1] = (slash_cid >> 8) & 0xFF
    rom[DATE_DAY_FILE] = 0xFF                  # 日 → chaîne vide
    rom[DATE_DAY_FILE + 1] = 0xFF

    return written, slash_cid, make_slash16()

