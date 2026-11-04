#!/usr/bin/env python3
"""Maps the kanji by OCR (manga-ocr) at LINE level + a majority vote per ID.

Idea: the font has no standard order, so we "read" the glyphs. manga-ocr
reads each rendered sentence; we only accept lines where the OCR length (excluding
spaces) == number of IDs (excluding $03FE) -> a clean 1:1 alignment. Each ID gets
one vote per character. Over ~2000 lines, a kanji seen N times becomes reliable by
majority vote (OCR hallucinations, which have the wrong length, are rejected).

Phases:
  ocr   : collects the unique lines (idx>=0x30F), OCR in memory, JSON cache.
  vote  : reads the cache, votes per ID, writes docs/kanji_font_index_ocr.csv + stats.

Usage:
  .venv-ocr/bin/python scripts/ocr_kanji_vote.py ocr
  python3 scripts/ocr_kanji_vote.py vote
"""
import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from nl_decompress import decompress, read_ptr_table, ROM  # noqa: E402
import render_text as rt  # noqa: E402

CACHE = ROOT / "docs" / "ocr_lines_cache.json"
OUT = ROOT / "docs" / "kanji_font_index_ocr.csv"
SPACE = 0x03FE
FIRST_TEXT_IDX = 0x30F
TABLE_COUNT = 0x600

# Characters that don't match a "full" game glyph (ignored in the
# alignment, manga-ocr adds/removes them freely).
DROP = set(" 　\n\t")


def load_km():
    km = {}
    for r in csv.DictReader((ROOT / "docs" / "kanji_font_index.csv").open()):
        u = r.get("unicode_char", "")
        if not u:
            continue
        try:
            km[int(r["char_id_hex"], 16)] = u
        except (ValueError, KeyError):
            pass
    return km


def collect_lines():
    """Returns {key_hex: [ids...]} for every unique dialogue line."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "dp", ROOT / "scripts" / "decompile_prologue_script.py")
    dp = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(dp)
    handlers = dp.opcode_handlers()
    sizes = {k: dp.opcode_size(v) for k, v in handlers.items()}
    feats = {k: dp.handler_features(v) for k, v in handlers.items()}
    km = load_km()

    import importlib
    es = importlib.import_module("extract_scenes")

    rom = ROM.read_bytes()
    tbl = read_ptr_table(rom, TABLE_COUNT)
    lines = {}
    for i, snes, off in tbl:
        if i < FIRST_TEXT_IDX or off is None or off >= len(rom):
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
        if g / nw < 0.30 or g < 30:
            continue
        tl, _ = es.scene_lines(out, handlers, sizes, feats, es.dp.load_font_map(), set(km))
        for _off, ids, _jp in tl:
            if len(ids) > 64:
                continue
            key = ".".join(f"{x:X}" for x in ids)
            lines[key] = ids
    return lines, rom


def phase_ocr():
    from manga_ocr import MangaOcr
    lines, rom = collect_lines()
    print(f"{len(lines)} unique lines to OCR")
    m = MangaOcr()
    cache = {}
    if CACHE.exists():
        cache = json.loads(CACHE.read_text())
    todo = [k for k in lines if k not in cache]
    print(f"{len(todo)} restantes (cache: {len(cache)})")
    for n, key in enumerate(todo, 1):
        ids = lines[key]
        im = rt.render_ids(rom, ids + [0xFFFF], scale=4, per_row=64)
        cache[key] = m(im)
        if n % 100 == 0:
            print(f"  {n}/{len(todo)}")
            CACHE.write_text(json.dumps(cache, ensure_ascii=False))
    CACHE.write_text(json.dumps(cache, ensure_ascii=False))
    print(f"OCR done, cache written ({len(cache)} lines)")


def _align(expected, ocr):
    """Needleman-Wunsch between the ID sequence (expected = known char or None)
    and the OCR string. Score: known anchor==ocr +2; anchor!=ocr -2;
    unknown vs ocr +0.3; gap -1.5. Returns the list of pairs (idx_id|None, char|None)."""
    n, m = len(expected), len(ocr)
    GAP = -1.5
    dp = [[0.0] * (m + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        dp[i][0] = dp[i - 1][0] + GAP
    for j in range(1, m + 1):
        dp[0][j] = dp[0][j - 1] + GAP
    for i in range(1, n + 1):
        e = expected[i - 1]
        for j in range(1, m + 1):
            c = ocr[j - 1]
            if e is None:
                s = 0.3
            else:
                s = 2.0 if e == c else -2.0
            dp[i][j] = max(dp[i - 1][j - 1] + s, dp[i - 1][j] + GAP, dp[i][j - 1] + GAP)
    # backtrack
    i, j = n, m
    pairs = []
    while i > 0 and j > 0:
        e = expected[i - 1]
        c = ocr[j - 1]
        s = 0.3 if e is None else (2.0 if e == c else -2.0)
        if dp[i][j] == dp[i - 1][j - 1] + s:
            pairs.append((i - 1, c))
            i -= 1
            j -= 1
        elif dp[i][j] == dp[i - 1][j] + GAP:
            pairs.append((i - 1, None))
            i -= 1
        else:
            j -= 1
    pairs.reverse()
    return pairs


def compute_votes(cache, anchor_map, thresh=0.7):
    """anchor_map: ID->char used as anchors. Returns (votes, n_lines)."""
    votes = defaultdict(Counter)
    aligned = 0
    for key, text in cache.items():
        ids = [int(x, 16) for x in key.split(".")]
        ids2 = [x for x in ids if x != SPACE]
        chars = [c for c in text if c not in DROP]
        if not chars or not ids2:
            continue
        expected = [anchor_map.get(x) for x in ids2]
        if not any(e is not None for e in expected):
            continue
        pairs = _align(expected, chars)
        good = tot = 0
        for idx, c in pairs:
            if idx is not None and expected[idx] is not None and c is not None:
                tot += 1
                if expected[idx] == c:
                    good += 1
        if tot == 0 or good / tot < thresh:
            continue
        aligned += 1
        for idx, c in pairs:
            if idx is not None and c is not None and expected[idx] is None:
                votes[ids2[idx]][c] += 1
    return votes, aligned


def phase_eval():
    """Validation: hides the known CJK kanji, votes, compares with the truth."""
    km = load_km()
    cache = json.loads(CACHE.read_text())
    held = {i: c for i, c in km.items() if any(ord(x) >= 0x4E00 for x in c)}
    anchors = {i: c for i, c in km.items() if i not in held}
    print(f"held-out: {len(held)} known kanji hidden; anchors: {len(anchors)} (kana)")
    for th in (0.6, 0.7, 0.8):
        votes, _ = compute_votes(cache, anchors, th)
        ok = bad = nf = 0
        for i, truth in held.items():
            if i not in votes:
                nf += 1
                continue
            pred, n = votes[i].most_common(1)[0]
            if pred == truth:
                ok += 1
            else:
                bad += 1
        tested = ok + bad
        print(f"  threshold {th}: predicted {tested}/{len(held)}; "
              f"right {ok} ({100*ok/tested if tested else 0:.0f}%), wrong {bad}, missing {nf}")


def phase_vote():
    km = load_km()
    cache = json.loads(CACHE.read_text())
    votes, aligned = compute_votes(cache, km, 0.7)
    print(f"lines kept: {aligned}/{len(cache)}")
    # build the voted mapping (kanji not known yet)
    new = {}
    strong = 0
    for i, cnt in votes.items():
        char, n = cnt.most_common(1)[0]
        total = sum(cnt.values())
        # anchor: if the ID is already known (kana), check the vote is consistent
        if i in km:
            continue
        if n >= 3 and n / total >= 0.6 and len(char) == 1:
            new[i] = char
            if n >= 5 and n / total >= 0.8:
                strong += 1
    print(f"new IDs mapped: {len(new)} ({strong} of them very reliable)")
    with OUT.open("w", encoding="utf-8") as f:
        f.write("char_id_hex,unicode_char,votes,total,confidence\n")
        for i in sorted(new):
            cnt = votes[i]
            char, n = cnt.most_common(1)[0]
            tot = sum(cnt.values())
            f.write(f"0x{i:04X},{char},{n},{tot},{n/tot:.2f}\n")
    print(f"wrote {OUT}")
    # couverture dialogue (occurrences)
    merged = dict(km)
    merged.update(new)
    occ = Counter()
    for key in cache:
        for x in key.split("."):
            v = int(x, 16)
            if v != SPACE and v < 0x800:
                occ[v] += 1
    tot = sum(occ.values())
    cov_km = 100 * sum(c for w, c in occ.items() if w in km) / tot
    cov_m = 100 * sum(c for w, c in occ.items() if w in merged) / tot
    print(f"couverture occurrences : connu {cov_km:.1f}% -> +OCR {cov_m:.1f}%")


if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else "ocr"
    if arg == "vote":
        phase_vote()
    elif arg == "eval":
        phase_eval()
    else:
        phase_ocr()
