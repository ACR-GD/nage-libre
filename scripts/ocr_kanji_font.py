#!/usr/bin/env python3
"""
Passe OCR Tesseract (jpn) sur la police kanji 16x16 (2bpp, ordre LT-LB-RT-RB).

Rend chaque glyphe en haute résolution noir-sur-blanc avec marge, puis lance
tesseract --psm 10 -l jpn. Écrit docs/kanji_font_ocr.csv.

Usage: python3 scripts/ocr_kanji_font.py [--all]
  (par défaut : seulement les cellules non déjà mappées dans kanji_font_index.csv)
"""
import csv
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
ROM = ROOT / "Nage Libre - Seijaku no Suishin (Japan).sfc"
INDEX_CSV = ROOT / "docs" / "kanji_font_index.csv"
OUT_CSV = ROOT / "docs" / "kanji_font_ocr.csv"

SCALE = 12
PAD = 48


def char_id_to_rom(cid: int) -> int:
    a = ((cid * 32) + 0x8000) & 0xFFFF
    if a >= 0x8000:
        return ((0x85 & 0x7F) * 0x8000) + (a - 0x8000)
    return ((0x86 & 0x7F) * 0x8000) + a


def tile(data: bytes):
    px = [[0] * 8 for _ in range(8)]
    for y in range(8):
        b0, b1 = data[y * 2], data[y * 2 + 1]
        for x in range(8):
            bit = 7 - x
            px[y][x] = ((b0 >> bit) & 1) | (((b1 >> bit) & 1) << 1)
    return px


def kanji_pixels(rom: bytes, off: int):
    t = [tile(rom[off + i * 16 : off + i * 16 + 16]) for i in range(4)]  # LT,LB,RT,RB
    g = [[0] * 16 for _ in range(16)]
    for y in range(8):
        for x in range(8):
            g[y][x] = t[0][y][x]
            g[y][x + 8] = t[2][y][x]
            g[y + 8][x] = t[1][y][x]
            g[y + 8][x + 8] = t[3][y][x]
    return g


# 0=blanc (fond) … 3=noir (encre)
INK = {0: 255, 1: 150, 2: 80, 3: 0}


def render(rom: bytes, off: int) -> Image.Image:
    g = kanji_pixels(rom, off)
    big = 16 * SCALE
    im = Image.new("L", (big + 2 * PAD, big + 2 * PAD), 255)
    px = im.load()
    for y in range(16):
        for x in range(16):
            v = INK[g[y][x]]
            for dy in range(SCALE):
                for dx in range(SCALE):
                    px[PAD + x * SCALE + dx, PAD + y * SCALE + dy] = v
    return im


def ocr(im: Image.Image, tmp: Path) -> str:
    im.save(tmp)
    try:
        r = subprocess.run(
            ["tesseract", str(tmp), "stdout", "-l", "jpn", "--psm", "10"],
            capture_output=True, text=True, timeout=20,
        )
        out = r.stdout.strip().replace(" ", "").replace("\n", "")
        return out
    except Exception:
        return ""


def load_known() -> dict[int, str]:
    known = {}
    if INDEX_CSV.is_file():
        with INDEX_CSV.open() as f:
            for row in csv.DictReader(f):
                if row.get("unicode_char"):
                    known[int(row["char_id_hex"], 16)] = row["unicode_char"]
    return known


def main() -> None:
    do_all = "--all" in sys.argv
    rom = ROM.read_bytes()
    known = load_known()

    cells = []
    for cid in range(0, 0x800, 2):
        off = char_id_to_rom(cid)
        if off + 64 <= len(rom) and any(rom[off : off + 64]):
            cells.append((cid, off))

    targets = cells if do_all else [(c, o) for c, o in cells if c not in known]
    total = len(targets)
    print(f"OCR sur {total} cellules (scale {SCALE}, --psm 10 -l jpn)…", flush=True)

    results = {}
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td) / "g.png"
        for i, (cid, off) in enumerate(targets):
            guess = ocr(render(rom, off), tmp)
            results[cid] = guess
            if (i + 1) % 50 == 0 or i + 1 == total:
                print(f"  {i+1}/{total}", flush=True)

    with OUT_CSV.open("w") as f:
        f.write("char_id_hex,rom_offset_hex,known_char,ocr_guess\n")
        for cid, off in cells:
            f.write(f"0x{cid:04X},0x{off:06X},{known.get(cid,'')},{results.get(cid,'')}\n")

    got = sum(1 for v in results.values() if v)
    print(f"Terminé. {got}/{total} glyphes ont produit un résultat OCR.")
    print(f"CSV: {OUT_CSV}")


if __name__ == "__main__":
    main()
