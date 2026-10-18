#!/usr/bin/env python3
"""Synchronise les corrections de docs/translations_review.csv vers les CSV par
scène (docs/scenes/scene_XXXX.csv), en réécrivant la colonne `en` repérée par
(scene_idx_hex, offset_hex).

Workflow de correction des traductions :
  1. éditer la colonne `en` de docs/translations_review.csv
  2. python3 scripts/sync_translations.py
  3. python3 build_full_translation.py   (reconstruit nl-full-en.sfc)
"""
import csv
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REVIEW = ROOT / "docs" / "translations_review.csv"
SCENES = ROOT / "docs" / "scenes"


def main():
    edits = defaultdict(dict)        # scene_idx_hex -> {offset_hex: en}
    for r in csv.DictReader(REVIEW.open(encoding="utf-8")):
        edits[r["scene_idx_hex"]][r["offset_hex"]] = (r.get("en") or "").strip()

    changed_files = 0
    changed_cells = 0
    for sidx, by_off in edits.items():
        path = SCENES / f"scene_{sidx[2:].upper().zfill(4)}.csv"
        if not path.exists():
            path = SCENES / f"scene_{int(sidx, 16):04X}.csv"
        if not path.exists():
            print(f"  introuvable : {sidx}")
            continue
        rows = list(csv.DictReader(path.open(encoding="utf-8")))
        if not rows:
            continue
        fields = list(rows[0].keys())
        touched = False
        for row in rows:
            new = by_off.get(row["offset_hex"])
            if new is not None and new != (row.get("en") or "").strip():
                row["en"] = new
                touched = True
                changed_cells += 1
        if touched:
            with path.open("w", newline="", encoding="utf-8") as fh:
                w = csv.DictWriter(fh, fieldnames=fields)
                w.writeheader()
                w.writerows(rows)
            changed_files += 1

    print(f"{changed_cells} cellule(s) `en` mises à jour dans {changed_files} scène(s).")


if __name__ == "__main__":
    main()
