#!/usr/bin/env python3
"""
Prologue screen 1 — English (v5, same hook as nl-prologue-en.sfc).

Output: nl-prologue-test-5.sfc
"""
import patch_nl_prologue_en as patch

patch.OUT_PATH = patch.OUT_PATH.parent / "nl-prologue-test-5.sfc"

if __name__ == "__main__":
    patch.main()
