#!/usr/bin/env python3
"""Translates every scene (jp_decoded -> en) with Google Cloud Translation v2.

- Key from .env (GOOGLE_API_KEY)
- Disk cache (docs/scenes/_translation_cache.json) to avoid repeat calls
- Segment batches + retries
"""
import csv
import glob
import json
import os
import time
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCENES = os.path.join(ROOT, "docs", "scenes")
CACHE = os.path.join(SCENES, "_translation_cache.json")
ENDPOINT = "https://translation.googleapis.com/language/translate/v2"
BATCH = 64


def load_key():
    for ln in open(os.path.join(ROOT, ".env")):
        if ln.startswith("GOOGLE_API_KEY="):
            return ln.strip().split("=", 1)[1]
    raise SystemExit("GOOGLE_API_KEY not found in .env")


def is_real(jp):
    return sum(1 for c in jp if c not in "□ \u3000") >= 2


def translate_batch(key, segs):
    data = json.dumps({"q": segs, "source": "ja", "target": "en", "format": "text"}).encode()
    req = urllib.request.Request(
        f"{ENDPOINT}?key={key}", data=data, headers={"Content-Type": "application/json"}
    )
    for attempt in range(5):
        try:
            d = json.load(urllib.request.urlopen(req, timeout=60))
            return [t["translatedText"] for t in d["data"]["translations"]]
        except urllib.error.HTTPError as e:
            body = e.read().decode()[:200]
            if e.code in (429, 500, 503) and attempt < 4:
                time.sleep(2 ** attempt)
                continue
            raise SystemExit(f"HTTP {e.code}: {body}")
    raise SystemExit("batch failed")


def main():
    key = load_key()
    cache = json.load(open(CACHE)) if os.path.exists(CACHE) else {}

    files = sorted(glob.glob(os.path.join(SCENES, "scene_*.csv")))
    # collect the unique segments to translate
    todo = set()
    for f in files:
        for r in csv.DictReader(open(f)):
            jp = (r.get("jp_decoded") or "").strip()
            if jp and is_real(jp) and jp not in cache:
                todo.add(jp)
    todo = sorted(todo)
    print(f"{len(todo)} unique segments to translate")

    for i in range(0, len(todo), BATCH):
        chunk = todo[i:i + BATCH]
        res = translate_batch(key, chunk)
        for src, en in zip(chunk, res):
            cache[src] = en
        json.dump(cache, open(CACHE, "w"), ensure_ascii=False, indent=0)
        print(f"  {min(i + BATCH, len(todo))}/{len(todo)}")
        time.sleep(0.2)

    # rewrite the CSVs with the en column filled in
    written = 0
    for f in files:
        rows = list(csv.DictReader(open(f)))
        fields = rows[0].keys() if rows else ["offset_hex", "n_ids", "slot_words", "jp_decoded", "en"]
        changed = False
        for r in rows:
            jp = (r.get("jp_decoded") or "").strip()
            if jp in cache and not (r.get("en") or "").strip():
                r["en"] = cache[jp]
                changed = True
                written += 1
        if changed:
            with open(f, "w", newline="") as fh:
                w = csv.DictWriter(fh, fieldnames=list(fields))
                w.writeheader()
                w.writerows(rows)
    print(f"{written} en cells filled in")


if __name__ == "__main__":
    main()
