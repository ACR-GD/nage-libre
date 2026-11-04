#!/usr/bin/env python3
"""Atlas of the UNmapped kanji glyphs, sorted by frequency in the dialogue.

Why: automatic OCR (Vision/manga-ocr) fails on this font (systematic
errors, ~12% verified accuracy). Mapping the most frequent glyphs by hand
is reliable and enough: top 200 -> ~97% coverage.

Output:
  docs/kanji_atlas/page_NN.png  — enlarged glyphs + rank number
  docs/kanji_manual.csv         — rank, char_id_hex, occ, unicode (to fill in)

Workflow: fill in the `unicode` column of docs/kanji_manual.csv by reading
the atlas, then `python3 scripts/build_kanji_atlas.py apply` merges it into
docs/kanji_font_index.csv and regenerates the scene CSVs.

Usage : python3 scripts/build_kanji_atlas.py [build|apply] [--top N]
"""
import csv
import sys
from collections import Counter
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from nl_decompress import decompress, read_ptr_table, ROM  # noqa: E402
import render_text as rt  # noqa: E402

ATLAS_DIR = ROOT / "docs" / "kanji_atlas"
MANUAL_CSV = ROOT / "docs" / "kanji_manual.csv"
INDEX_CSV = ROOT / "docs" / "kanji_font_index.csv"
CACHE = ROOT / "docs" / "ocr_lines_cache.json"
SPACE = 0x03FE


def known_ids():
    ids = set()
    for r in csv.DictReader(INDEX_CSV.open()):
        if r.get("unicode_char"):
            try:
                ids.add(int(r["char_id_hex"], 16))
            except (ValueError, KeyError):
                pass
    return ids


def dialogue_occ():
    """Glyph occurrences in the extracted dialogue lines."""
    import json
    occ = Counter()
    if CACHE.exists():
        for key in json.loads(CACHE.read_text()):
            for x in key.split("."):
                v = int(x, 16)
                if v != SPACE:
                    occ[v] += 1
        return occ
    # fallback: decompress again
    rom = ROM.read_bytes()
    for i, snes, off in read_ptr_table(rom, 0x600):
        if i < 0x30F or off is None or off >= len(rom):
            continue
        try:
            out, _ = decompress(rom, off, dst_limit=0x4000)
        except Exception:
            continue
        for k in range(0, len(out) - 1, 2):
            v = out[k] | (out[k + 1] << 8)
            if v != SPACE and v < 0x800:
                occ[v] += 1
    return occ


def phase_build(top):
    rom = ROM.read_bytes()
    known = known_ids()
    occ = dialogue_occ()
    unknown = [(w, c) for w, c in occ.most_common() if w not in known and w < 0x800]
    unknown = unknown[:top]
    print(f"{len(unknown)} glyphs to map (top {top} by frequency)")

    ATLAS_DIR.mkdir(parents=True, exist_ok=True)
    with MANUAL_CSV.open("w", encoding="utf-8") as f:
        f.write("rank,char_id_hex,occ,unicode\n")
        for rank, (w, c) in enumerate(unknown, 1):
            f.write(f"{rank},0x{w:04X},{c},\n")

    # pages: 8 columns x 12 rows = 96 glyphs per page
    COLS, ROWS = 8, 12
    per_page = COLS * ROWS
    scale = 5
    cell_g = 16 * scale          # 80 px glyph
    label_h = 16
    cell_w = cell_g + 12
    cell_h = cell_g + label_h + 6
    pages = (len(unknown) + per_page - 1) // per_page
    for pg in range(pages):
        chunk = unknown[pg * per_page:(pg + 1) * per_page]
        W = COLS * cell_w + 8
        H = ROWS * cell_h + 8
        im = Image.new("RGB", (W, H), (235, 235, 235))
        d = ImageDraw.Draw(im)
        for k, (w, c) in enumerate(chunk):
            rank = pg * per_page + k + 1
            cx = (k % COLS) * cell_w + 4
            cy = (k // COLS) * cell_h + 4
            d.text((cx, cy), f"{rank}:{w:04X}", fill=(180, 0, 0))
            g = rt.glyph_pixels(rom, w)
            gimg = Image.new("L", (16, 16))
            gp = gimg.load()
            for y in range(16):
                for x in range(16):
                    gp[x, y] = rt.INK[g[y][x]]
            gimg = gimg.resize((cell_g, cell_g), Image.NEAREST)
            im.paste(gimg, (cx, cy + label_h))
        out = ATLAS_DIR / f"page_{pg:02d}.png"
        im.save(out)
    print(f"{pages} page(s) -> {ATLAS_DIR}")
    print(f"CSV to fill in: {MANUAL_CSV}")


def phase_apply():
    """Merges kanji_manual.csv (filled-in unicode column) into the index."""
    add = {}
    for r in csv.DictReader(MANUAL_CSV.open()):
        u = (r.get("unicode") or "").strip()
        if u:
            add[int(r["char_id_hex"], 16)] = u
    print(f"{len(add)} manual mappings filled in")
    if not add:
        print("Nothing to merge (unicode column empty).")
        return
    rows = list(csv.DictReader(INDEX_CSV.open()))
    have = {int(r["char_id_hex"], 16) for r in rows}
    fields = rows[0].keys() if rows else ["char_id_hex", "char_id_dec",
                                          "rom_offset_hex", "snes_addr_hex",
                                          "unicode_char", "notes"]
    # update the existing ones, add the new ones
    for r in rows:
        cid = int(r["char_id_hex"], 16)
        if cid in add and not r.get("unicode_char"):
            r["unicode_char"] = add[cid]
            r["notes"] = "manual"
    for cid, u in add.items():
        if cid not in have:
            rows.append({"char_id_hex": f"0x{cid:04X}", "char_id_dec": str(cid),
                         "rom_offset_hex": "", "snes_addr_hex": "",
                         "unicode_char": u, "notes": "manual"})
    rows.sort(key=lambda r: int(r["char_id_hex"], 16))
    with INDEX_CSV.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(fields))
        w.writeheader()
        w.writerows(rows)
    print(f"index updated: {INDEX_CSV}")
    print("Regenerate the scenes: python3 scripts/extract_scenes.py")


if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else "build"
    top = 300
    if "--top" in sys.argv:
        top = int(sys.argv[sys.argv.index("--top") + 1])
    if arg == "apply":
        phase_apply()
    else:
        phase_build(top)
