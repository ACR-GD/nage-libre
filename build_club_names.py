#!/usr/bin/env python3
"""Noms de clubs pour l'ÉCRAN DE SÉLECTION (Nage Libre).

L'écran de sélection de club lit les noms via une table de pointeurs 24-bit
(4 octets/entrée) à $87:E346, qui pointe vers les chaînes kanji en $87:85FF...
Ce chemin est DISTINCT de la boîte de PV en combat (table $81:AF5B), déjà
relocalisée vers les noms complets en $AF par build_names_full.

Comme $81:AF5B ne pointe plus vers $87:85FF.., ces slots ne servent QUE pour la
sélection de club : on y réécrit *sur place* des libellés anglais COURTS (la
boîte est étroite), remplis d'espaces jusqu'à la largeur du slot (efface le
suffixe 部 et toute rémanence), terminés par FFFF.

Source des kanji/traductions : docs/nage-libre-kanji-kana - names_translation.csv
(idx 227..241). Libellés courts définis ici pour tenir dans la boîte.

apply(rom, alloc) est appelé par build_full_translation.py (allocateur partagé).
"""
import struct

from patch_prologue_v3 import JP_SPACE, encode_en

# (file_off, slot_words, libellé court).  slot_words = nb de glyphes du nom JP
# d'origine (1 mot/glyphe) ; le moteur s'arrête au FFFF qui suit.
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
]


def apply(rom: bytearray, alloc):
    """Réécrit les noms de clubs (courts) en place à $87:85FF.. Renvoie le nb
    écrit. Lève si un libellé dépasse son slot."""
    written = 0
    for off, slot, en in CLUBS:
        ids = encode_en(en, alloc)
        while len(ids) > 1 and ids[-1] == JP_SPACE:
            ids.pop()
        if len(ids) > slot:
            raise SystemExit(
                f"Club '{en}' = {len(ids)} mots > slot {slot} @ 0x{off:06X}")
        ids = ids + [JP_SPACE] * (slot - len(ids)) + [0xFFFF]
        for i, cid in enumerate(ids):
            struct.pack_into("<H", rom, off + i * 2, cid)
        written += 1
    return written
