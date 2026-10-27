#!/usr/bin/env python3
"""
Fenêtres de la commande PAGER en combat (« WHO » + ordres) en anglais.

Contexte :
  - À l'ouverture de la fenêtre, le renderer $80:F8DC décompresse le bloc
    graphique $A1:8FC7 dans le buffer de police WRAM $7E:2000 (tuile T à
    $7E:2000 + (T-$80)*16), puis DMA vers VRAM (BG3). Ce bloc contient les
    prénoms en kanji 16x16 (彩香 舞 惟 美姫 嶺子, tuiles $A0-$BF) et les ordres
    (攻撃 防御 回復 必殺 着替 移動, tuiles $C0-$F7). Les étiquettes romaji
    (AYAKA, WHO…) des tuiles $80-$9F sont déjà en anglais dans le bloc d'origine.
  - Les lignes sont posées par $87:8000 à partir de gabarits fixes (banque $87) :
    2 cellules 16x16 (4 tuiles) par libellé, 1 cellule pour 舞 et 惟. La
    main-curseur (sprite) suit la 4e tuile : on ne peut pas élargir les lignes.

Correctif : le hook de sortie du renderer (build_combat_command_menu, $80:FA80)
reconnaît le bloc PAGER (signature) et recopie (MVN $BF -> $7E:2200) des tuiles
pré-rendues par-dessus les kanji : chaque libellé est écrit dans les tuiles du
haut de SES cellules d'origine avec une police majuscule étroite (5 px, même
graisse que le menu de commande), tuiles du bas vidées. Aucun gabarit, curseur
ni code du jeu n'est modifié.

apply(rom, jp_rom) est appelé par build_full_translation.py avant CMD.apply,
qui lit hook_params() pour assembler la branche PAGER du hook.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT / "scripts"))
from nl_decompress import decompress  # noqa: E402

BLOCK_FILE = 0x108FC7          # $A1:8FC7, bloc graphique PAGER (compressé)
BUF_BASE = 0x2000              # $7E:2000 = tuile $80
FIRST_TILE, END_TILE = 0xA0, 0xF8   # tuiles kanji remplacées ($A0-$F7)

# (tuile haut-gauche, nb de tuiles de large, libellé) — bas = haut + $10
LABELS = [
    (0xA0, 4, "AYAKA"),        # 彩香
    (0xA4, 2, "MAI"),          # 舞
    (0xA6, 2, "YUI"),          # 惟
    (0xA8, 4, "MIKI"),         # 美姫
    (0xAC, 4, "RYOKO"),        # 嶺子
    (0xC0, 4, "FIGHT"),        # 攻撃 (comme le menu de commande)
    (0xC4, 4, "GUARD"),        # 防御
    (0xC8, 4, "HEAL"),         # 回復
    (0xCC, 4, "SUPER"),        # 必殺
    (0xE0, 4, "DRESS"),        # 着替
    (0xE4, 4, "MOVE"),         # 移動
]

# Majuscules étroites 7 rangées (rangée 0 vide, comme FONT du menu de commande)
GLYPHS = {
    "A": [".###.", "##.##", "##.##", "##.##", "#####", "##.##", "##.##"],
    "D": ["####.", "##.##", "##.##", "##.##", "##.##", "##.##", "####."],
    "E": ["#####", "##...", "##...", "####.", "##...", "##...", "#####"],
    "F": ["#####", "##...", "##...", "####.", "##...", "##...", "##..."],
    "G": [".####", "##...", "##...", "##.##", "##.##", "##.##", ".####"],
    "H": ["##.##", "##.##", "##.##", "#####", "##.##", "##.##", "##.##"],
    "I": ["####", ".##.", ".##.", ".##.", ".##.", ".##.", "####"],
    "K": ["##.##", "##.##", "####.", "###..", "####.", "##.##", "##.##"],
    "L": ["##...", "##...", "##...", "##...", "##...", "##...", "#####"],
    "M": ["#...#", "##.##", "#####", "#.#.#", "#...#", "#...#", "#...#"],
    "O": [".###.", "##.##", "##.##", "##.##", "##.##", "##.##", ".###."],
    "P": ["####.", "##.##", "##.##", "####.", "##...", "##...", "##..."],
    "R": ["####.", "##.##", "##.##", "####.", "##.##", "##.##", "##.##"],
    "S": [".####", "##...", "##...", ".###.", "...##", "...##", "####."],
    "T": ["######", "..##..", "..##..", "..##..", "..##..", "..##..", "..##.."],
    "U": ["##.##", "##.##", "##.##", "##.##", "##.##", "##.##", ".###."],
    "V": ["##.##", "##.##", "##.##", "##.##", "##.##", ".###.", "..#.."],
    "Y": ["##.##", "##.##", "##.##", ".###.", ".##..", ".##..", ".##.."],
}

# Tuiles pré-rendues en banque $BF (zone libre après les messages de combat)
DATA_FILE = 0x1FF000           # $BF:F000
DATA_END = 0x200000
BANK = 0xBF


def _render(word, width_px):
    """Bitmap 8 rangées (liste d'entiers de width_px bits), lettres + 1 px d'espace."""
    cols = []
    for k, c in enumerate(word):
        if k:
            cols.append([0] * 7)
        g = GLYPHS[c]
        for x in range(len(g[0])):
            cols.append([1 if g[y][x] == "#" else 0 for y in range(7)])
    if len(cols) > width_px:
        raise SystemExit(f"PAGER : « {word} » = {len(cols)} px > {width_px} px.")
    rows = [0] * 8
    for x, col in enumerate(cols):
        for y in range(7):
            if col[y]:
                rows[y + 1] |= 1 << (width_px - 1 - x)
    return rows


def _tile(rows8):
    """8 rangées 8 bits -> tuile 2bpp (couleur 1, comme le menu de commande)."""
    t = bytearray(16)
    for y, r in enumerate(rows8):
        t[2 * y] = r
    return bytes(t)


def build_tiles():
    """Tuiles $A0-$F7 (16 o chacune) : libellés en haut, reste vide."""
    tiles = {t: bytes(16) for t in range(FIRST_TILE, END_TILE)}
    for top, n, word in LABELS:
        rows = _render(word, 8 * n)
        for i in range(n):
            shift = 8 * (n - 1 - i)
            tiles[top + i] = _tile([(r >> shift) & 0xFF for r in rows])
    return b"".join(tiles[t] for t in range(FIRST_TILE, END_TILE))


def _signature(jp_rom):
    """Mots du bloc décompressé (identiques en ROM anglaise) servant de signature."""
    out, _ = decompress(jp_rom, BLOCK_FILE, dst_limit=0x4000)
    out = bytes(out)
    if len(out) != 0x800:
        raise SystemExit(f"Bloc PAGER $A1:8FC7 inattendu ({len(out)} o).")
    w = lambda o: out[o] | (out[o + 1] << 8)
    a1 = (FIRST_TILE - 0x80) * 16 + 4          # 彩 (tuile $A0)
    a2 = (0xC0 - 0x80) * 16 + 6                # 攻 (tuile $C0)
    return [(BUF_BASE + a1, w(a1)), (BUF_BASE + a2, w(a2))]


_params = None


def hook_params():
    """Paramètres de la branche PAGER du hook $80:FA80 (après apply)."""
    if _params is None:
        raise SystemExit("build_pager_menu.apply() doit précéder CMD.apply().")
    return _params


def apply(rom: bytearray, jp_rom: bytes):
    global _params
    data = build_tiles()
    if DATA_FILE + len(data) > DATA_END:
        raise SystemExit("Dépassement zone $BF (fenêtres PAGER).")
    if any(b not in (0x00, 0xFF) for b in rom[DATA_FILE:DATA_FILE + len(data)]):
        raise SystemExit(f"Zone $BF:{0x8000 + DATA_FILE % 0x8000:04X} déjà occupée.")
    rom[DATA_FILE:DATA_FILE + len(data)] = data
    _params = {
        "sigs": _signature(jp_rom),
        "src_bank": BANK,
        "src": 0x8000 + DATA_FILE % 0x8000,
        "dst": BUF_BASE + (FIRST_TILE - 0x80) * 16,
        "len": len(data),
    }
    return {"labels": " / ".join(w for _, _, w in LABELS), "bytes": len(data)}
