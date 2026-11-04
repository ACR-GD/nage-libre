#!/usr/bin/env python3
"""Verification atlas of the mapped kanji/kana (docs/kanji_font_index.csv).

For each mapped ID, renders side by side the GAME GLYPH (left, from the ROM
font) and the assigned CHARACTER (right, Hiragino font), with the hex ID, the note
(confidence) and the number of occurrences. The "auto(to verify)" entries (the most
likely to be wrong) come FIRST.

To fix one: find a cell where glyph ≠ character, then edit the
`unicode_char` column of docs/kanji_font_index.csv on the `char_id_hex` row shown.

Output: docs/kanji_atlas/verify_NN.png
"""
import csv
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import render_text as rt  # noqa: E402

INDEX = ROOT / "docs" / "kanji_font_index.csv"
MANUAL = ROOT / "docs" / "kanji_manual.csv"
ATLAS = ROOT / "docs" / "kanji_atlas"
CJK = "/System/Library/Fonts/ヒラギノ角ゴシック W4.ttc"

# review priority order (the most doubtful first)
ORDER = {"auto(to verify)": 0, "manual": 1}


def main():
    rom = rt.ROM.read_bytes()
    occ = {}
    if MANUAL.exists():
        for r in csv.DictReader(MANUAL.open()):
            try:
                occ[int(r["char_id_hex"], 16)] = int(r["occ"])
            except (ValueError, KeyError):
                pass

    rows = []
    for r in csv.DictReader(INDEX.open()):
        u = (r.get("unicode_char") or "").strip()
        if not u:
            continue
        cid = int(r["char_id_hex"], 16)
        note = (r.get("notes") or "").strip()
        rows.append({"cid": cid, "u": u, "note": note, "occ": occ.get(cid, 0)})

    # sort: priority note first, then by decreasing occurrences
    rows.sort(key=lambda r: (ORDER.get(r["note"], 9), -r["occ"], r["cid"]))

    font = ImageFont.truetype(CJK, 40)
    small = ImageFont.truetype(CJK, 11)
    tiny = ImageFont.truetype(CJK, 10)
    COLS, ROWS = 8, 11
    per = COLS * ROWS
    gs = 52
    cw, ch = gs * 2 + 18, gs + 30
    ATLAS.mkdir(parents=True, exist_ok=True)
    pages = (len(rows) + per - 1) // per
    for pg in range(pages):
        chunk = rows[pg * per:(pg + 1) * per]
        W, H = COLS * cw + 8, ROWS * ch + 8
        im = Image.new("RGB", (W, H), (248, 248, 248))
        d = ImageDraw.Draw(im)
        for k, r in enumerate(chunk):
            cx = (k % COLS) * cw + 4
            cy = (k // COLS) * ch + 4
            # banner: ID + occ, colour by confidence
            tag = "AUTO?" if r["note"] == "auto(to verify)" else (
                "man" if r["note"] == "manual" else "ok")
            col = (200, 0, 0) if tag == "AUTO?" else (
                (80, 80, 80) if tag == "man" else (0, 130, 0))
            d.text((cx, cy), f'0x{r["cid"]:04X} {tag}', fill=col, font=small)
            if r["occ"]:
                d.text((cx, cy + 12), f'×{r["occ"]}', fill=(120, 120, 120), font=tiny)
            # game glyph
            g = rt.glyph_pixels(rom, r["cid"])
            gi = Image.new("L", (16, 16))
            gp = gi.load()
            for y in range(16):
                for x in range(16):
                    gp[x, y] = rt.INK[g[y][x]]
            im.paste(gi.resize((gs, gs), Image.NEAREST), (cx, cy + 24))
            # assigned character
            d.text((cx + gs + 8, cy + 26), r["u"], fill=(0, 0, 0), font=font)
            # separator
            d.line([(cx + gs + 4, cy + 24), (cx + gs + 4, cy + 24 + gs)],
                   fill=(210, 210, 210))
        out = ATLAS / f"verify_{pg:02d}.png"
        im.save(out)
    n_auto = sum(1 for r in rows if r["note"] == "auto(to verify)")
    print(f"{len(rows)} mapped kanji -> {pages} page(s) docs/kanji_atlas/verify_*.png")
    print(f"  including {n_auto} 'auto(to verify)' (first, marked AUTO? in red)")


if __name__ == "__main__":
    main()
