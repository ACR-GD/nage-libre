#!/usr/bin/env python3
"""
Traduction des NOMS de personnages de l'écran d'anniversaire (Nage Libre).

Le moteur $80:F4A7 affiche chaque nom en DEUX morceaux : un « nom de famille »
et un « prénom », pointés par deux tables de pointeurs 24-bit :

    $81:AF5B  table NOMS DE FAMILLE  (5 entrées × 3 octets) → $87:8077/807D/...
    $81:B087  table PRÉNOMS          (5 entrées × 3 octets) → $87:82D9/82DF/...

Les chaînes d'origine sont des IDs kanji, dans des slots très serrés (1–3 glyphes)
→ impossible d'y caser un nom romanisé sur place. On RELOCALISE : on écrit le nom
complet « Prénom Nom » (encodage paires VWF, comme le reste) dans une zone libre
de la banque $87, puis on repointe l'entrée NOM DE FAMILLE dessus et l'entrée
PRÉNOM sur une chaîne vide (FFFF) — le nom complet s'affiche à la position du nom
de famille, rien à la position du prénom.

Personnages (ordre de la table) :
    0 桜井彩香  1 姫ノ木舞  2 霧島惟  3 静本美姫  4 葵嶺子

apply(rom, alloc) est appelé par build_full_translation.py (allocateur partagé).
"""
from pathlib import Path

from patch_prologue_v3 import JP_SPACE, encode_en, _rows_to_2bpp

ROOT = Path(__file__).parent

# Tables de pointeurs 24-bit (offsets fichier)
SURNAME_TBL = 0x0AF5B          # $81:AF5B
GIVEN_TBL = 0x0B087            # $81:B087
N_CHARS = 5

# Zone libre banque $87 pour les chaînes relocalisées
DATA_FILE = 0x03FA0C           # $87:FA0C
DATA_BANK = 0x87
DATA_ADDR = 0xFA0C             # adresse 16-bit dans la banque
DATA_END = 0x03FFF0            # marge avant fin de banque

# Date d'anniversaire « N月 N日 » : chaînes mono-glyphe pointées par le code.
# On rend « N / N » : 月 → « / », 日 → vide. (slots = 1 mot chacun)
DATE_MONTH_FILE = 0x038965     # $87:8965  (月, ID 32C)
DATE_DAY_FILE = 0x038969       # $87:8969  (日, ID 2C8)

# Noms romanisés, ordre de la table. Ordre occidental (Prénom Nom).
# 惟 / 嶺子 : lectures incertaines (à confirmer).
NAMES = [
    "Ayaka Sakurai",      # 桜井彩香
    "Mai Himenoki",       # 姫ノ木舞
    "Yui Kirishima",      # 霧島惟  (惟 = Yui ?)
    "Miki Shizumoto",     # 静本美姫
    "Reiko Aoi",          # 葵嶺子  (嶺子 = Reiko ?)
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
    """Encode les noms (via l'allocateur partagé), les écrit en zone libre, et
    repointe les tables. Renvoie (written, slash_cid, slash_glyph) — l'appelant
    écrit les tuiles de paires puis le glyphe « / » à char_id_to_rom(slash_cid)."""
    if len(NAMES) != N_CHARS:
        raise SystemExit(f"NAMES doit contenir {N_CHARS} entrées.")

    # Encodage + largeur commune (les noms se redessinent à la MÊME position en
    # faisant défiler ; on remplit chacun jusqu'à la largeur max avec des espaces
    # pour effacer le nom précédent — sinon rémanence des lettres en trop).
    enc = []
    for name in NAMES:
        ids = encode_en(name, alloc)
        while len(ids) > 1 and ids[-1] == JP_SPACE:
            ids.pop()
        enc.append(ids)
    width = max(len(ids) for ids in enc)

    cursor = DATA_FILE
    empty_addr = DATA_ADDR                  # chaîne vide partagée (prénoms)
    rom[cursor:cursor + 2] = b"\xFF\xFF"
    cursor += 2

    written = []
    for i, ids in enumerate(enc):
        ids = ids + [JP_SPACE] * (width - len(ids)) + [0xFFFF]
        addr = DATA_ADDR + (cursor - DATA_FILE)
        if cursor + len(ids) * 2 > DATA_END:
            raise SystemExit("Dépassement zone libre $87:FA0C pour les noms.")
        for j, cid in enumerate(ids):
            rom[cursor + j * 2] = cid & 0xFF
            rom[cursor + j * 2 + 1] = (cid >> 8) & 0xFF
        cursor += len(ids) * 2
        _write_ptr(rom, SURNAME_TBL, i, DATA_BANK, addr)
        _write_ptr(rom, GIVEN_TBL, i, DATA_BANK, empty_addr)
        written.append((NAMES[i], addr, width))

    # Date « N月 N日 » → « N / N » : glyphe « / » 16×16 dédié dans la case du mois.
    slash_cid = alloc.get("/", "/")          # ID réservé (réécrit en glyphe 16×16)
    rom[DATE_MONTH_FILE] = slash_cid & 0xFF
    rom[DATE_MONTH_FILE + 1] = (slash_cid >> 8) & 0xFF
    rom[DATE_DAY_FILE] = 0xFF                  # 日 → chaîne vide
    rom[DATE_DAY_FILE + 1] = 0xFF

    return written, slash_cid, make_slash16()
