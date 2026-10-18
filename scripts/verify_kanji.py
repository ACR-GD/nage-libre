#!/usr/bin/env python3
"""Atlas de vérification des kanji/kana mappés (docs/kanji_font_index.csv).

Pour chaque ID mappé, rend côte à côte le GLYPHE DU JEU (gauche, depuis la police
ROM) et le CARACTÈRE assigné (droite, police Hiragino), avec l'ID hex, la note
(confiance) et le nb d'occurrences. Les entrées « auto(à vérifier) » (les plus
susceptibles d'être fausses) sont placées EN PREMIER.

Pour corriger : repérer une case où glyphe ≠ caractère, puis éditer la colonne
`unicode_char` de docs/kanji_font_index.csv à la ligne `char_id_hex` indiquée.

Sortie : docs/kanji_atlas/verify_NN.png
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

# ordre de priorité de revue (les plus douteux d'abord)
ORDER = {"auto(à vérifier)": 0, "manuel": 1}


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

    # tri : note prioritaire d'abord, puis par occurrences décroissantes
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
            # bandeau : ID + occ, couleur selon confiance
            tag = "AUTO?" if r["note"] == "auto(à vérifier)" else (
                "man" if r["note"] == "manuel" else "ok")
            col = (200, 0, 0) if tag == "AUTO?" else (
                (80, 80, 80) if tag == "man" else (0, 130, 0))
            d.text((cx, cy), f'0x{r["cid"]:04X} {tag}', fill=col, font=small)
            if r["occ"]:
                d.text((cx, cy + 12), f'×{r["occ"]}', fill=(120, 120, 120), font=tiny)
            # glyphe du jeu
            g = rt.glyph_pixels(rom, r["cid"])
            gi = Image.new("L", (16, 16))
            gp = gi.load()
            for y in range(16):
                for x in range(16):
                    gp[x, y] = rt.INK[g[y][x]]
            im.paste(gi.resize((gs, gs), Image.NEAREST), (cx, cy + 24))
            # caractère assigné
            d.text((cx + gs + 8, cy + 26), r["u"], fill=(0, 0, 0), font=font)
            # séparateur
            d.line([(cx + gs + 4, cy + 24), (cx + gs + 4, cy + 24 + gs)],
                   fill=(210, 210, 210))
        out = ATLAS / f"verify_{pg:02d}.png"
        im.save(out)
    n_auto = sum(1 for r in rows if r["note"] == "auto(à vérifier)")
    print(f"{len(rows)} kanji mappés -> {pages} page(s) docs/kanji_atlas/verify_*.png")
    print(f"  dont {n_auto} 'auto(à vérifier)' (en tête, marqués AUTO? en rouge)")


if __name__ == "__main__":
    main()
