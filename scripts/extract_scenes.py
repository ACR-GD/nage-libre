#!/usr/bin/env python3
"""Extraction of ALL the compressed text scenes of Nage Libre.

Full pipeline:
  1. pointer table $8A:8000 -> compressed source of each scene
  2. static decompression (scripts/nl_decompress.py, reverse of $80:F8D8)
  3. walk of the opcode program ($83:8103) to locate the text lines
     ("line" opcodes = the ADC #$64C0/STA $09 pattern) and their offset in
     the $7F:64C0 block
  4. per scene: a working CSV (offset, slot, partial JP, EN) + an accurate PNG of the
     lines (16x16 font rendering) to READ the kanji not mapped yet.

Output: docs/scenes/scene_XXXX.csv / .png  +  docs/scenes/_index.csv

Usage : python3 scripts/extract_scenes.py [--limit N] [--no-png]
"""
import csv
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from nl_decompress import decompress, read_ptr_table, ROM  # noqa: E402

_spec = importlib.util.spec_from_file_location(
    "dp", ROOT / "scripts" / "decompile_prologue_script.py")
dp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(dp)

OUTDIR = ROOT / "docs" / "scenes"
TABLE_COUNT = 0x600
DENSITY_MIN = 0.30
GLYPH_MIN = 30

SPACE = 0x03FE          # space marker in the stream
FIRST_GLYPH = 0x10      # first real glyph (あ); below = control codes


def is_glyph(v):
    """Valid font glyph slot.

    Addressing is char_id*32 and a glyph takes 64 bytes: real glyphs
    are therefore at EVEN IDs >= 0x10. An odd ID points into the middle of a
    glyph (garbage rendering) and 0x00..0x0F is below the first glyph: in both
    cases it's a control code, not text.
    """
    return v != 0xFFFF and v >= FIRST_GLYPH and (v & 1) == 0


def load_km():
    km = set()
    p = ROOT / "docs" / "kanji_font_index.csv"
    for r in csv.DictReader(p.open()):
        try:
            if r.get("unicode_char"):
                km.add(int(r["char_id_hex"], 16))
        except (ValueError, KeyError):
            pass
    return km


def _decode(ids, fmap):
    out = []
    for v in ids:
        if v == SPACE:
            out.append(" ")
        elif not is_glyph(v):
            continue          # control code: ignored (neither □ nor a character)
        else:
            out.append(fmap.get(v, "□"))   # unmapped real glyph -> □
    return "".join(out)


def line_quality(ids, km):
    """(number of real glyphs, number of mapped glyphs) in a line, excluding spaces/control codes."""
    glyphs = [v for v in ids if is_glyph(v) and v != SPACE]
    return len(glyphs), sum(1 for v in glyphs if v in km)


def is_text_line(ids, km):
    """A real dialogue line (≥2 mapped glyphs, mostly mapped glyphs)."""
    n, kn = line_quality(ids, km)
    return kn >= 2 and n >= 2 and kn / n >= 0.5


def scene_lines(out, handlers, sizes, feats, fmap, km):
    """Locates the text lines of the decompressed block `out`.

    1) Walk of the opcode program ($83:8103): "line" opcodes -> offsets.
    2) Robust fallback (format-independent): scan of every $FFFF-terminated
       string with a high glyph density, past the end of the
       program. Recovers the text of scenes the walk can't parse.
    Returns (text_lines, prog_end); text_lines = [(offset, ids, jp)]."""
    def word(o):
        return out[o] | (out[o + 1] << 8) if o + 1 < len(out) else 0xFFFF

    lines = {}
    pos = 0
    for _ in range(2000):
        opc = word(pos)
        if opc == 0xFFFF or opc not in handlers:
            break
        size = sizes.get(opc, 0) or 2
        nopr = (size - 2) // 2
        opr = [word(pos + 2 + 2 * j) for j in range(nopr)]
        ft = feats[opc]
        if ft["textline"] and nopr >= 1 and opr[0] >= 0x100:
            soff = opr[0]
            ids = []
            o = soff
            for _ in range(80):
                v = word(o)
                if v == 0xFFFF:
                    break
                ids.append(v)
                o += 2
            if ids:
                lines[soff] = ids
        pos += size
    prog_end = pos

    # Fallback: scan of $FFFF-terminated glyph strings.
    nwords = len(out) // 2
    o = 0
    start = None
    run = []
    while o < nwords:
        v = word(o * 2)
        if v == 0xFFFF:
            if run and start is not None and start not in lines:
                if is_text_line(run, km):
                    lines[start] = list(run)
            run = []
            start = None
        else:
            if start is None:
                start = o * 2
            run.append(v)
            if len(run) > 64:  # no real dialogue line is that long
                run = []
                start = None
        o += 1

    text_lines = []
    for off, ids in sorted(lines.items()):
        clean = [v for v in ids if is_glyph(v) or v == SPACE]
        text_lines.append((off, clean, _decode(clean, fmap)))
    return text_lines, prog_end


def slots(offsets):
    """slot_words[offset] = gap to the next offset − 1 (terminator)."""
    offs = sorted(set(offsets))
    out = {}
    for i, o in enumerate(offs):
        nxt = offs[i + 1] if i + 1 < len(offs) else o + 0x40
        out[o] = (nxt - o) // 2 - 1
    return out


def main():
    args = sys.argv[1:]
    limit = None
    do_png = "--no-png" not in args
    if "--limit" in args:
        limit = int(args[args.index("--limit") + 1])

    rom = ROM.read_bytes()
    km = load_km()
    handlers = dp.opcode_handlers()
    sizes = {k: dp.opcode_size(v) for k, v in handlers.items()}
    feats = {k: dp.handler_features(v) for k, v in handlers.items()}
    fmap = dp.load_font_map()

    if do_png:
        import render_text as rt

    OUTDIR.mkdir(parents=True, exist_ok=True)
    tbl = read_ptr_table(rom, TABLE_COUNT)

    index_rows = []
    n_done = 0
    for i, snes, off in tbl:
        if off is None or off >= len(rom):
            continue
        try:
            out, _ = decompress(rom, off, dst_limit=0x4000)
        except Exception:
            continue
        nw = len(out) // 2
        if nw < 8:
            continue
        words = [out[k] | (out[k + 1] << 8) for k in range(0, len(out) - 1, 2)]
        g = sum(1 for w in words if w in km)
        if g / nw < DENSITY_MIN or g < GLYPH_MIN:
            continue

        lines, prog_end = scene_lines(out, handlers, sizes, feats, fmap, km)
        # rejects "graphics" scenes (abnormally long lines) and
        # numeric / status lines (control codes, not dialogue)
        lines = [ln for ln in lines if len(ln[1]) <= 64 and is_text_line(ln[1], km)]
        if not lines or sum(line_quality(ln[1], km)[0] for ln in lines) < 12:
            continue

        # dedupe by offset, sort
        seen = {}
        for soff, ids, jp in lines:
            if soff not in seen:
                seen[soff] = (ids, jp)
        offs = sorted(seen)
        sl = slots(offs)

        csv_path = OUTDIR / f"scene_{i:04X}.csv"
        with csv_path.open("w", encoding="utf-8") as f:
            f.write("offset_hex,n_ids,slot_words,jp_decoded,en\n")
            for soff in offs:
                ids, jp = seen[soff]
                jpq = jp.replace('"', "'")
                f.write(f"0x{soff:04X},{len(ids)},{sl[soff]},\"{jpq}\",\n")

        png_name = ""
        if do_png:
            render_ids = []
            for soff in offs:
                render_ids += seen[soff][0] + [0xFFFF]
            try:
                im = rt.render_ids(rom, render_ids, scale=3, per_row=40)
                png_path = OUTDIR / f"scene_{i:04X}.png"
                im.save(png_path)
                png_name = png_path.name
            except Exception:
                pass

        total_glyphs = sum(len(seen[o][0]) for o in offs)
        index_rows.append((i, snes, len(offs), total_glyphs, csv_path.name, png_name))
        n_done += 1
        if limit and n_done >= limit:
            break

    idx_path = OUTDIR / "_index.csv"
    with idx_path.open("w", encoding="utf-8") as f:
        f.write("scene_idx_hex,snes_src,n_lines,n_glyphs,csv,png\n")
        for i, snes, nl, ng, c, p in index_rows:
            f.write(f"0x{i:04X},0x{snes:06X},{nl},{ng},{c},{p}\n")

    tot_lines = sum(r[2] for r in index_rows)
    tot_glyph = sum(r[3] for r in index_rows)
    print(f"{len(index_rows)} scenes extracted -> {OUTDIR}")
    print(f"  {tot_lines} text lines, {tot_glyph} glyphs")
    print(f"  index : {idx_path}")


if __name__ == "__main__":
    main()
