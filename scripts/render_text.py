#!/usr/bin/env python3
"""Rendu d'une suite d'IDs de police 16-bit (police kanji 16x16, 2bpp) en PNG.

Sert à *lire* visuellement le texte ROM dont le mapping unicode est incertain.
Réutilise l'agencement de tuiles LT,LB,RT,RB validé par scripts/ocr_kanji_font.py.
"""
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
ROM = ROOT / "Nage Libre - Seijaku no Suishin (Japan).sfc"

INK = {0: 255, 1: 150, 2: 80, 3: 0}


def char_id_to_rom(cid: int) -> int:
    a = ((cid * 32) + 0x8000) & 0xFFFF
    if a >= 0x8000:
        return ((0x85 & 0x7F) * 0x8000) + (a - 0x8000)
    return ((0x86 & 0x7F) * 0x8000) + a


def _tile(data: bytes):
    px = [[0] * 8 for _ in range(8)]
    for y in range(8):
        b0, b1 = data[y * 2], data[y * 2 + 1]
        for x in range(8):
            bit = 7 - x
            px[y][x] = ((b0 >> bit) & 1) | (((b1 >> bit) & 1) << 1)
    return px


def glyph_pixels(rom: bytes, cid: int):
    off = char_id_to_rom(cid)
    t = [_tile(rom[off + i * 16: off + i * 16 + 16]) for i in range(4)]  # LT,LB,RT,RB
    g = [[0] * 16 for _ in range(16)]
    for y in range(8):
        for x in range(8):
            g[y][x] = t[0][y][x]
            g[y][x + 8] = t[2][y][x]
            g[y + 8][x] = t[1][y][x]
            g[y + 8][x + 8] = t[3][y][x]
    return g


def render_ids(rom: bytes, ids, scale=3, per_row=24, pad=2):
    """Rend une liste d'IDs en grille (FFFF = saut de ligne, 0x0000 = espace)."""
    rows = [[]]
    for w in ids:
        if w == 0xFFFF:
            rows.append([])
        else:
            rows[-1].append(w)
    rows = [r for r in rows if r] or [[]]
    # découpe en sous-lignes de per_row
    flat_rows = []
    for r in rows:
        for i in range(0, len(r), per_row):
            flat_rows.append(r[i:i + per_row])
    w_cells = max((len(r) for r in flat_rows), default=1)
    W = w_cells * 16 * scale + 2 * pad
    H = len(flat_rows) * 16 * scale + 2 * pad
    im = Image.new("L", (W, H), 220)
    px = im.load()
    for ry, r in enumerate(flat_rows):
        for cx, cid in enumerate(r):
            g = glyph_pixels(rom, cid)
            ox = pad + cx * 16 * scale
            oy = pad + ry * 16 * scale
            for y in range(16):
                for x in range(16):
                    v = INK[g[y][x]]
                    for dy in range(scale):
                        for dx in range(scale):
                            px[ox + x * scale + dx, oy + y * scale + dy] = v
    return im


def main():
    import sys
    rom = ROM.read_bytes()
    # démo : bloc du méchant $87:89C5
    off = ((0x87 & 0x7F) * 0x8000) + (0x89C5 - 0x8000)
    ids = []
    i = off
    while i < off + 200:
        w = rom[i] | (rom[i + 1] << 8)
        ids.append(w)
        i += 2
        if ids.count(0xFFFF) >= 6:
            break
    out = ROOT / "docs" / "render_villain.png"
    render_ids(rom, ids, scale=4).save(out)
    print("écrit", out)


if __name__ == "__main__":
    main()
