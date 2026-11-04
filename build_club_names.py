#!/usr/bin/env python3
"""Club names for the SELECTION SCREEN (Nage Libre).

The club selection screen reads the names through a table of 24-bit pointers
(4 bytes per entry) at $87:E346, which points to the kanji strings at $87:85FF...
This path is SEPARATE from the battle HP box (table $81:AF5B), already
relocated to the full names in $AF by build_names_full.

Since $81:AF5B no longer points to $87:85FF.., these slots are ONLY used for
club selection: we rewrite SHORT English labels there *in place* (the
box is narrow), padded with spaces up to the slot width (which erases the
部 suffix and any ghosting), terminated by FFFF.

Source of the kanji/translations: docs/nage-libre-kanji-kana - names_translation.csv
(idx 227..242). The short labels are defined here so they fit in the box.

apply(rom, alloc) is called by build_full_translation.py (shared allocator).
"""
import struct

from patch_prologue_v3 import JP_SPACE, encode_en

# (file_off, slot_words, short label).  slot_words = number of glyphs in the original
# JP name (1 word per glyph); the engine stops at the FFFF that follows.
CLUBS = [
    (0x0385FF, 4, "Basket"),    # バスケ部  Basketball
    (0x038609, 4, "Tennis"),    # テニス部
    (0x038613, 3, "Kendo"),     # 剣道部
    (0x03861B, 3, "Karate"),    # 空手部
    (0x038623, 3, "Kyudo"),     # 弓道部    archery
    (0x03862B, 5, "Lacrosse"),  # ラクロス部
    (0x038637, 4, "Gymnast"),   # 新体操部
    (0x038641, 5, "Occult"),    # オカルト研
    (0x03864D, 3, "Sci."),      # 科学部    science
    (0x038655, 3, "Dance"),     # 日舞部    Japanese dance
    (0x03865D, 3, "Floral"),    # 華道部    flower arrangement
    (0x038665, 4, "Music"),     # 軽音楽部  light music
    (0x03866F, 3, "Drama"),     # 演劇部
    (0x038677, 3, "Manga"),     # 漫画部
    (0x03867F, 3, "Crafts"),    # 手芸部    handicraft
    (0x038687, 4, "No club"),   # 一般生徒  no club (16th entry of $87:E346)
]


def apply(rom: bytearray, alloc):
    """Rewrites the (short) club names in place at $87:85FF.. Returns the number
    written. Raises if a label is longer than its slot."""
    written = 0
    for off, slot, en in CLUBS:
        ids = encode_en(en, alloc)
        while len(ids) > 1 and ids[-1] == JP_SPACE:
            ids.pop()
        if len(ids) > slot:
            raise SystemExit(
                f"Club '{en}' = {len(ids)} words > slot {slot} @ 0x{off:06X}")
        ids = ids + [JP_SPACE] * (slot - len(ids)) + [0xFFFF]
        for i, cid in enumerate(ids):
            struct.pack_into("<H", rom, off + i * 2, cid)
        written += 1
    return written
