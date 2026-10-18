#!/usr/bin/env python3
"""Mappe les kanji par OCR (manga-ocr) au niveau LIGNE + vote majoritaire par ID.

Idée : la police n'a pas d'ordre standard, donc on « lit » les glyphes. manga-ocr
lit chaque phrase rendue ; on n'accepte que les lignes où la longueur OCR (hors
espaces) == nombre d'IDs (hors $03FE) -> alignement 1:1 propre. Chaque ID reçoit
un vote par caractère. Sur ~2000 lignes, un kanji vu N fois devient fiable par
vote majoritaire (les hallucinations OCR, de mauvaise longueur, sont rejetées).

Phases :
  ocr   : collecte les lignes uniques (idx>=0x30F), OCR en mémoire, cache JSON.
  vote  : lit le cache, vote par ID, écrit docs/kanji_font_index_ocr.csv + stats.

Usage :
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

# Caractères qui ne correspondent pas à un glyphe game « plein » (à ignorer dans
# l'alignement, manga-ocr les ajoute/retire librement).
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
    """Retourne {key_hex: [ids...]} pour toutes les lignes de dialogue uniques."""
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
    print(f"{len(lines)} lignes uniques à OCR")
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
    print(f"OCR terminé, cache écrit ({len(cache)} lignes)")


def _align(expected, ocr):
    """Needleman-Wunsch entre la séquence d'IDs (expected = char connu ou None)
    et la chaîne OCR. Score : ancre connue==ocr +2 ; ancre!=ocr -2 ;
    inconnu vs ocr +0.3 ; gap -1.5. Retourne la liste de paires (idx_id|None, char|None)."""
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
    """anchor_map : ID->char utilisés comme ancres. Retourne (votes, n_lignes)."""
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
    """Validation : cache les kanji CJK connus, vote, compare à la vérité."""
    km = load_km()
    cache = json.loads(CACHE.read_text())
    held = {i: c for i, c in km.items() if any(ord(x) >= 0x4E00 for x in c)}
    anchors = {i: c for i, c in km.items() if i not in held}
    print(f"held-out : {len(held)} kanji connus cachés ; ancres : {len(anchors)} (kana)")
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
        print(f"  seuil {th}: prédits {tested}/{len(held)} ; "
              f"justes {ok} ({100*ok/tested if tested else 0:.0f}%), faux {bad}, absents {nf}")


def phase_vote():
    km = load_km()
    cache = json.loads(CACHE.read_text())
    votes, aligned = compute_votes(cache, km, 0.7)
    print(f"lignes retenues : {aligned}/{len(cache)}")
    # construit le mapping voté (kanji non encore connus)
    new = {}
    strong = 0
    for i, cnt in votes.items():
        char, n = cnt.most_common(1)[0]
        total = sum(cnt.values())
        # anchor : si l'ID est déjà connu (kana), on vérifie la cohérence du vote
        if i in km:
            continue
        if n >= 3 and n / total >= 0.6 and len(char) == 1:
            new[i] = char
            if n >= 5 and n / total >= 0.8:
                strong += 1
    print(f"nouveaux IDs mappés : {len(new)} (dont {strong} très fiables)")
    with OUT.open("w", encoding="utf-8") as f:
        f.write("char_id_hex,unicode_char,votes,total,confidence\n")
        for i in sorted(new):
            cnt = votes[i]
            char, n = cnt.most_common(1)[0]
            tot = sum(cnt.values())
            f.write(f"0x{i:04X},{char},{n},{tot},{n/tot:.2f}\n")
    print(f"écrit {OUT}")
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
