#!/usr/bin/env python3
"""Verification sheets of the 16x16 glyphs (2bpp kanji font, bank $85).

Each cell: the enlarged glyph (colour 1 = black stroke, 3 = blue stroke,
2 = light grey outline), its ID, its current mapping (docs/kanji_font_index.csv,
red = unmapped) and its number of occurrences in the scene text.
Unlike render_text.render_ids (which inks every non-zero pixel and turns the
kanji into "blobs"), the planes are kept separate: the kanji are readable by eye.

Usage: python3 scripts/glyph_sheets.py [used|all] [out_dir]
  used : IDs present in the scene lines (default), sorted by ID
  all  : every even ID 0x10..0x7E6 of the font
"""
import csv
import sys
from collections import Counter
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from nl_decompress import decompress, read_ptr_table, ROM  # noqa: E402
import render_text as rt  # noqa: E402

SPACE = 0x03FE
LAST_GLYPH = 0x07E6
COLORS = {1: (0, 0, 0), 2: (215, 215, 215), 3: (60, 60, 230)}
SCALE = 5
COLS, ROWS = 10, 8
CELL_W, CELL_H = 16 * SCALE + 40, 16 * SCALE + 34
LABEL_FONT = "/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc"


def scene_glyph_counts(rom):
    """Occurrences of each even ID >= 0x10 in the lines of the scene CSVs."""
    tbl = {i: off for i, _s, off in read_ptr_table(rom, 0x600) if off}
    occ = Counter()
    for path in sorted((ROOT / "docs" / "scenes").glob("scene_*.csv")):
        sidx = int(path.stem.split("_")[1], 16)
        out, _ = decompress(rom, tbl[sidx], dst_limit=0x4000)
        for r in csv.DictReader(path.open(encoding="utf-8")):
            o = int(r["offset_hex"], 16)
            for _ in range(80):
                if o + 1 >= len(out):
                    break
                v = out[o] | (out[o + 1] << 8)
                if v == 0xFFFF:
                    break
                if v >= 0x10 and not v & 1 and v != SPACE:
                    occ[v] += 1
                o += 2
    return occ


def load_map():
    return {int(r["char_id_hex"], 16): r["unicode_char"]
            for r in csv.DictReader((ROOT / "docs" / "kanji_font_index.csv").open(encoding="utf-8"))}


def draw_sheet(rom, ids, fmap, occ, font, small):
    img = Image.new("RGB", (COLS * CELL_W, ROWS * CELL_H), "white")
    d = ImageDraw.Draw(img)
    for k, cid in enumerate(ids):
        x0 = (k % COLS) * CELL_W + 4
        y0 = (k // COLS) * CELL_H + 4
        d.rectangle([x0 - 2, y0 - 2, x0 + 16 * SCALE + 1, y0 + 16 * SCALE + 1], outline=(235, 235, 235))
        for y, row in enumerate(rt.glyph_pixels(rom, cid)):
            for x, v in enumerate(row):
                if v:
                    d.rectangle([x0 + x * SCALE, y0 + y * SCALE,
                                 x0 + x * SCALE + SCALE - 1, y0 + y * SCALE + SCALE - 1],
                                fill=COLORS[v])
        cur = (fmap.get(cid) or "").strip()
        d.text((x0 + 16 * SCALE + 4, y0), cur or "?", font=font,
               fill=(0, 120, 0) if cur else (220, 0, 0))
        d.text((x0, y0 + 16 * SCALE + 3), f"{cid:03X} ×{occ.get(cid, 0)}", font=small, fill=(90, 90, 90))
    return img


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "used"
    out_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "docs" / "glyph_sheets"
    out_dir.mkdir(parents=True, exist_ok=True)
    rom = ROM.read_bytes()
    occ = scene_glyph_counts(rom)
    ids = sorted(occ) if mode == "used" else list(range(0x10, LAST_GLYPH + 1, 2))
    fmap = load_map()
    font = ImageFont.truetype(LABEL_FONT, 26)
    small = ImageFont.truetype(LABEL_FONT, 14)
    per = COLS * ROWS
    for n in range(0, len(ids), per):
        chunk = ids[n:n + per]
        draw_sheet(rom, chunk, fmap, occ, font, small).save(
            out_dir / f"{mode}_{n // per:02d}_{chunk[0]:03X}-{chunk[-1]:03X}.png")
    print(f"{len(ids)} glyphs -> {out_dir} ({(len(ids) + per - 1) // per} sheets)")


if __name__ == "__main__":
    main()
