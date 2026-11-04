#!/usr/bin/env python3
"""
The PAGER command windows in battle ("WHO" + orders) in English.

Context:
  - When the window opens, the $80:F8DC renderer decompresses the graphics
    block $A1:8FC7 into the WRAM font buffer $7E:2000 (tile T at
    $7E:2000 + (T-$80)*16), then DMAs it to VRAM (BG3). This block holds the
    given names in 16x16 kanji (彩香 舞 惟 美姫 嶺子, tiles $A0-$BF) and the orders
    (攻撃 防御 回復 必殺 着替 移動, tiles $C0-$F7). The romaji labels
    (AYAKA, WHO…) in tiles $80-$9F are already in English in the original block.
  - The lines are laid out by $87:8000 from fixed templates (bank $87):
    2 16x16 cells (4 tiles) per label, 1 cell for 舞 and 惟. The
    hand cursor (a sprite) follows the 4th tile: the lines can't be made wider.

Fix: the renderer's exit hook (build_combat_command_menu, $80:FA80)
jumps (JML) to a branch in $BF, right after the tiles (bank $80 is
full), which recognises the PAGER block (signature) and copies (MVN $BF -> $7E:2200)
pre-rendered tiles over the kanji: each label is written in the top tiles
of ITS original cells with a narrow capital font (5 px, the same
weight as the command menu), bottom tiles cleared. No template, cursor
or game code is changed.

apply(rom, jp_rom) is called by build_full_translation.py before CMD.apply,
which reads hook_params() to assemble the hook's PAGER branch.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT / "scripts"))
from nl_decompress import decompress  # noqa: E402

BLOCK_FILE = 0x108FC7          # $A1:8FC7, PAGER graphics block (compressed)
BUF_BASE = 0x2000              # $7E:2000 = tile $80
FIRST_TILE, END_TILE = 0xA0, 0xF8   # kanji tiles replaced ($A0-$F7)

# (top-left tile, width in tiles, label) — bottom = top + $10
LABELS = [
    (0xA0, 4, "AYAKA"),        # 彩香
    (0xA4, 2, "MAI"),          # 舞
    (0xA6, 2, "YUI"),          # 惟
    (0xA8, 4, "MIKI"),         # 美姫
    (0xAC, 4, "RYOKO"),        # 嶺子
    (0xC0, 4, "FIGHT"),        # 攻撃 (as in the command menu)
    (0xC4, 4, "GUARD"),        # 防御
    (0xC8, 4, "HEAL"),         # 回復
    (0xCC, 4, "SUPER"),        # 必殺
    (0xE0, 4, "DRESS"),        # 着替
    (0xE4, 4, "MOVE"),         # 移動
]

# Narrow capitals, 7 rows (row 0 empty, like the command menu's FONT)
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

# Pre-rendered tiles in bank $BF (free area after the battle messages)
DATA_FILE = 0x1FF000           # $BF:F000
DATA_END = 0x200000
BANK = 0xBF


def _render(word, width_px):
    """8-row bitmap (list of width_px-bit integers), letters + 1 px of spacing."""
    cols = []
    for k, c in enumerate(word):
        if k:
            cols.append([0] * 7)
        g = GLYPHS[c]
        for x in range(len(g[0])):
            cols.append([1 if g[y][x] == "#" else 0 for y in range(7)])
    if len(cols) > width_px:
        raise SystemExit(f"PAGER: \"{word}\" = {len(cols)} px > {width_px} px.")
    rows = [0] * 8
    for x, col in enumerate(cols):
        for y in range(7):
            if col[y]:
                rows[y + 1] |= 1 << (width_px - 1 - x)
    return rows


def _tile(rows8):
    """8 rows of 8 bits -> 2bpp tile (colour 1, like the command menu)."""
    t = bytearray(16)
    for y, r in enumerate(rows8):
        t[2 * y] = r
    return bytes(t)


def build_tiles():
    """Tiles $A0-$F7 (16 bytes each): labels at the top, the rest empty."""
    tiles = {t: bytes(16) for t in range(FIRST_TILE, END_TILE)}
    for top, n, word in LABELS:
        rows = _render(word, 8 * n)
        for i in range(n):
            shift = 8 * (n - 1 - i)
            tiles[top + i] = _tile([(r >> shift) & 0xFF for r in rows])
    return b"".join(tiles[t] for t in range(FIRST_TILE, END_TILE))


def _signature(jp_rom):
    """Words of the decompressed block (identical in the English ROM) used as a signature."""
    out, _ = decompress(jp_rom, BLOCK_FILE, dst_limit=0x4000)
    out = bytes(out)
    if len(out) != 0x800:
        raise SystemExit(f"Bloc PAGER $A1:8FC7 inattendu ({len(out)} o).")
    w = lambda o: out[o] | (out[o + 1] << 8)
    a1 = (FIRST_TILE - 0x80) * 16 + 4          # 彩 (tile $A0)
    a2 = (0xC0 - 0x80) * 16 + 6                # 攻 (tile $C0)
    return [(BUF_BASE + a1, w(a1)), (BUF_BASE + a2, w(a2))]


_params = None


def hook_params():
    """Parameters of the PAGER branch of the $80:FA80 hook (after apply)."""
    if _params is None:
        raise SystemExit("build_pager_menu.apply() must run before CMD.apply().")
    return _params


def apply(rom: bytearray, jp_rom: bytes):
    global _params
    data = build_tiles()
    if DATA_FILE + len(data) > DATA_END:
        raise SystemExit("$BF area overflow (PAGER windows).")
    if any(b not in (0x00, 0xFF) for b in rom[DATA_FILE:DATA_FILE + len(data)]):
        raise SystemExit(f"Area $BF:{0x8000 + DATA_FILE % 0x8000:04X} already in use.")
    rom[DATA_FILE:DATA_FILE + len(data)] = data
    code_file = DATA_FILE + len(data)              # hook branch, right after
    _params = {
        "code_file": code_file,
        "code_snes": (BANK << 16) | (0x8000 + code_file % 0x8000),
        "sigs": _signature(jp_rom),
        "src_bank": BANK,
        "src": 0x8000 + DATA_FILE % 0x8000,
        "dst": BUF_BASE + (FIRST_TILE - 0x80) * 16,
        "len": len(data),
    }
    return {"labels": " / ".join(w for _, _, w in LABELS), "bytes": len(data)}
