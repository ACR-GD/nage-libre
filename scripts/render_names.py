#!/usr/bin/env python3
"""Rend les 247 chaînes du bloc de noms $87:8077.. en planches PNG étiquetées.

Chaque ligne = [index décimal en police latine 8x8] [glyphes kanji 16x16 du nom].
Sert à identifier/romaniser les noms (lectures non mappées dans l'index kanji).
Sortie : docs/names_render/page_NN.png  + index console (idx -> offset SNES).
"""
from pathlib import Path
from PIL import Image
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from patch_prologue_v3 import FONT  # 8x8 latin
from scripts.render_text import glyph_pixels  # type: ignore

ROM = (ROOT / "Nage Libre - Seijaku no Suishin (Japan).sfc").read_bytes()
BLOCK_START = 0x038077
BLOCK_END = 0x0386D9
INK = {0: 255, 1: 150, 2: 80, 3: 0}
SCALE = 4
PER_PAGE = 24


def collect():
    """(offset_snes, [ids]) pour chaque chaîne FFFF-terminée."""
    out, cur, off0 = [], [], BLOCK_START
    i = BLOCK_START
    start = i
    while i < BLOCK_END:
        w = ROM[i] | (ROM[i + 1] << 8)
        i += 2
        if w == 0xFFFF:
            snes = 0x8000 + (start - 0x038000)
            out.append((snes, cur))
            cur, start = [], i
        else:
            cur.append(w)
    return out


def latin_glyph(ch):
    """16x16 pixel grid pour un caractère latin (8x8 en haut-gauche)."""
    g = [[0] * 16 for _ in range(16)]
    if ch in FONT:
        top, bot = FONT[ch]
        for y in range(8):
            for x in range(8):
                g[y][x] = 3 if (top[y] >> (7 - x)) & 1 else 0
    return g


def render_page(entries, path):
    rows = []
    for idx, snes, ids in entries:
        label = f"{idx:03d}:{snes:04X} "
        cells = [latin_glyph(c) for c in label] + [glyph_pixels(ROM, w) for w in ids]
        rows.append(cells)
    wc = max(len(r) for r in rows)
    W = wc * 16 * SCALE + 4
    H = len(rows) * 16 * SCALE + 4
    im = Image.new("L", (W, H), 220)
    px = im.load()
    for ry, cells in enumerate(rows):
        for cx, g in enumerate(cells):
            ox, oy = 2 + cx * 16 * SCALE, 2 + ry * 16 * SCALE
            for y in range(16):
                for x in range(16):
                    v = INK[g[y][x]]
                    for dy in range(SCALE):
                        for dx in range(SCALE):
                            px[ox + x * SCALE + dx, oy + y * SCALE + dy] = v
    im.save(path)


def main():
    names = collect()
    outdir = ROOT / "docs" / "names_render"
    outdir.mkdir(exist_ok=True)
    print(f"{len(names)} chaînes")
    indexed = [(i, snes, ids) for i, (snes, ids) in enumerate(names)]
    for p in range(0, len(indexed), PER_PAGE):
        page = indexed[p:p + PER_PAGE]
        path = outdir / f"page_{p // PER_PAGE:02d}.png"
        render_page(page, path)
        print("écrit", path.name, f"(idx {page[0][0]}..{page[-1][0]})")


if __name__ == "__main__":
    main()
