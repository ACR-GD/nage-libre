#!/usr/bin/env python3
"""
Prologue screen 1 — alias of patch_nl_prologue_en.py (minimal 14-word insertion).

Output: nl-prologue-erase-en.sfc
"""
from pathlib import Path

import patch_nl_prologue_en as patch

patch.OUT_PATH = patch.OUT_PATH.parent / "nl-prologue-erase-en.sfc"

if __name__ == "__main__":
    patch.main()
