#!/usr/bin/env python3
"""Re-decodes the `jp_decoded` column of the scene CSVs and of translations_review.csv
from the ROM, with the up-to-date docs/kanji_font_index.csv table.

Only touches `jp_decoded` (the `en` column is kept), unlike
extract_scenes.py, which rewrites the CSVs with an empty `en` column.

Usage : python3 scripts/redecode_jp.py
"""
import csv
import importlib.util
import io
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from nl_decompress import decompress, read_ptr_table, ROM  # noqa: E402

_spec = importlib.util.spec_from_file_location("es", ROOT / "scripts" / "extract_scenes.py")
es = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(es)

SCENES = ROOT / "docs" / "scenes"
REVIEW = ROOT / "docs" / "translations_review.csv"


def read_ids(out, off):
    ids = []
    while off + 1 < len(out) and len(ids) < 80:
        v = out[off] | (out[off + 1] << 8)
        if v == 0xFFFF:
            break
        ids.append(v)
        off += 2
    return ids


def rewrite_csv(path, keyfn, decoded):
    """Replaces `jp_decoded` on the rows whose key is in `decoded`; keeps the line endings."""
    raw = path.read_bytes().decode("utf-8")
    nl = "\r\n" if "\r\n" in raw else "\n"
    rows = list(csv.reader(io.StringIO(raw, newline="")))
    hdr = rows[0]
    ji = hdr.index("jp_decoded")
    n = 0
    for r in rows[1:]:
        jp = decoded.get(keyfn(dict(zip(hdr, r))))
        if jp is not None and r[ji] != jp:
            r[ji] = jp
            n += 1
    buf = io.StringIO()
    csv.writer(buf, lineterminator=nl).writerows(rows)
    path.write_bytes(buf.getvalue().encode("utf-8"))
    return n


def main():
    rom = ROM.read_bytes()
    fmap = es.dp.load_font_map()
    tbl = {i: off for i, _s, off in read_ptr_table(rom, 0x600) if off}

    decoded = {}                      # (scene_hex, offset_hex) -> jp
    n_scene = 0
    for path in sorted(SCENES.glob("scene_*.csv")):
        sidx = path.stem.split("_")[1]
        out, _ = decompress(rom, tbl[int(sidx, 16)], dst_limit=0x4000)
        per = {}
        for r in csv.DictReader(path.open(encoding="utf-8")):
            ids = [v for v in read_ids(out, int(r["offset_hex"], 16)) if es.is_glyph(v) or v == es.SPACE]
            per[r["offset_hex"]] = es._decode(ids, fmap)
        n_scene += rewrite_csv(path, lambda d: d["offset_hex"], per)
        decoded.update({(sidx, o): jp for o, jp in per.items()})

    n_review = rewrite_csv(REVIEW, lambda d: (d["scene_idx_hex"], d["offset_hex"]), decoded)
    unmapped = sum(jp.count("□") for jp in decoded.values())
    print(f"jp_decoded updated: {n_scene} scene rows, {n_review} review rows "
          f"({unmapped} glyph(s) still unmapped □)")


if __name__ == "__main__":
    main()
