#!/usr/bin/env python3
"""
Battle messages (Nage Libre): English sentences assembled in the right order.

The battle log (bottom box, 28 columns: col 2..29, 2 rows $15/$17)
is assembled at run time by the routines $81:98A4..$81:9D14 and $83:90E0..$83:9307:
    [name] + fragment + [number] + fragment
Each fragment is loaded by a fixed pattern
    LDA #lo / STA $09 / LDA #hi / STA $0A / LDA #bank / STA $0B ; JSL $80:F4A7
We REPOINT each site to an English fragment of its own (encoded as
8x16 half-width, see build_scene_injection.encode_hw), placed at $BF:8000+.
So the fragments are no longer limited to the size of the Japanese slots, and two
sites that shared a particle (は = "takes" / "gains" / "recovers")
each get their own text.

Names in messages: the routine $81:9D19 (messages + status sheet $81:C0B0)
reads the shared table $81:AF5B, encoded as 16x16 pairs with a trailing space
that depends on parity. We give it a PARALLEL half-width table
(given name without a trailing space, surname = "␣X."), hence exact spacing.
The HP HUD ($81:BA82, raw copy of 16x16 tiles) keeps the pair table.

HP HUD: $81:BA82 shows the name with index X then the one with index Y. The callers
$81:873D / $81:8746 loaded X = surname -> "K.Yui". We swap the
two loads -> "Yui K.", "Shizuko N.".

apply(rom) is called by build_full_translation.py (after NF.apply / N.apply).
"""
import struct

import build_character_names as N
import build_names_full as NF
from build_scene_injection import encode_hw

POOL_BANK = 0xBF
POOL_FILE = 0x1F8000           # $BF:8000
POOL_END = 0x200000

MSG_COLS = 28                  # usable width of the bottom box (col 2..29)

# (SNES site of the "LDA #lo", original JP target, English text)
# Typical lines (name <= 7 letters, number <= 3 digits):
#   "Shizuko attacks! Gem bonus!"   "Shizuko takes 12 damage!!"
#   "Yui gains 3 DEF!!"             "Yui recovers 8 HP!!"
SITES = [
    # --- attack / special move ---
    (0x8198AF, 0x8786DF, " attacks!"),
    (0x8198D5, 0x878897, "'s special move!!"),
    # --- misc ---
    (0x8198F8, 0x878731, "Changing outfits..."),
    (0x81991B, 0x878749, "Run for it!!"),
    (0x81993E, 0x8787B3, "Don't run! Wait!!"),
    # --- damage (player -> opponent, opponent -> player) ---
    (0x819979, 0x878789, " Gem bonus!"),
    (0x81999B, 0x8786E9, " takes "),
    (0x8199B8, 0x8786ED, " damage!!"),
    (0x8199D6, 0x878797, "It did no damage!!"),
    (0x819A11, 0x878789, " Gem bonus!"),
    (0x819A33, 0x8786E9, " takes "),
    (0x819A50, 0x8786ED, " damage!!"),
    (0x819A6E, 0x878797, "It did no damage!!"),
    # --- defense ---
    (0x819A99, 0x878879, "Gem bonus!"),
    (0x819ABB, 0x8786E9, " gains "),
    (0x819AD8, 0x878705, " DEF!!"),
    (0x819B03, 0x878879, "Gem bonus!"),
    (0x819B25, 0x8786E9, " gains "),
    (0x819B42, 0x878705, " DEF!!"),
    # --- healing ---
    (0x819B6D, 0x878879, "Gem bonus!"),
    (0x819B8F, 0x8786E9, " recovers "),
    (0x819BAC, 0x8786FB, " HP!!"),
    (0x819BD7, 0x878879, "Gem bonus!"),
    (0x819BF9, 0x8786E9, " recovers "),
    (0x819C16, 0x8786FB, " HP!!"),
    # --- running away ---
    (0x819C41, 0x87876F, "...barely got away..."),
    (0x819C55, 0x878755, "...got caught!!"),
    (0x819C80, 0x8787D5, "...she got away."),
    (0x819C94, 0x8787C7, "...caught up to her!"),
    # --- victory: "[name] is defeated!!" / "[N]0 Gold earned!!" ---
    (0x819CCB, 0x8787EB, " is defeated!!"),
    (0x819CFE, 0x8787F7, " Gold earned!!"),
    # --- unknown name ---
    (0x81BFD3, 0x8786D9, "??"),
    (0x81C118, 0x8786D9, "??"),
    # --- stat increases (col 8): "[stat] up by [N]!!" ---
    (0x8390E8, 0x878819, "HP up by "),
    (0x839105, 0x87880D, "!!"),
    (0x839138, 0x878821, "Power up by "),
    (0x839155, 0x87880D, "!!"),
    (0x839188, 0x878829, "Defense up by "),
    (0x8391A5, 0x87880D, "!!"),
    (0x8391D8, 0x87883D, "Speed up by "),
    (0x8391F5, 0x87880D, "!!"),
    (0x839228, 0x878833, "Spirit up by "),
    (0x839245, 0x87880D, "!!"),
    (0x83927A, 0x878847, "Level up to "),
    (0x839297, 0x87886B, "!!"),
    # --- club unlocked: "[club]" then, on the next row at col 5 ---
    (0x8392D3, 0x878851, ""),
    (0x8392F8, 0x878855, "is now selectable!!"),
]

# HP HUD: (file offset, original bytes, patched bytes)
HUD_SWAPS = [
    (0x00873D, bytes.fromhex("ac8410ae8610"), bytes.fromhex("ac8610ae8410")),  # player
    (0x008746, bytes.fromhex("ac9c10ae9e10"), bytes.fromhex("ac9e10ae9c10")),  # opponent
]

# $81:9D19 : LDA $81AF58,X / LDA $81AF59,X / LDA $81AF5A,X (index 1-based * 3)
NAME_LOOKUP_OPERANDS = (0x009D38, 0x009D3E, 0x009D44)


def lorom(snes):
    return ((snes >> 16) & 0x7F) * 0x8000 + (snes & 0x7FFF)


def _hw_names(rom):
    """Parallel table (244 entries): half-width texts for $81:9D19.
    None = keep the original pointer (untranslated entry)."""
    en_by_idx, idx_by_off, role_by_idx = NF._load_en()
    out = [None] * NF.N_ENTRIES
    for e in range(NF.N_ENTRIES):
        addr16, _bank = NF._ptr_target(rom, NF.NAME_TBL, e)
        idx = idx_by_off.get(addr16)
        if idx is None or idx not in en_by_idx:
            continue
        name = en_by_idx[idx]
        if role_by_idx.get(idx) == "surname":
            out[e] = f" {name[0].upper()}."
        elif idx < 227:
            out[e] = name[:7]          # same truncation as the HUD (NF.apply)
    for i, (given, surname_init) in enumerate(N.MAIN_PLAYERS):
        out[i] = " " + surname_init.strip()
        out[100 + i] = given
    return out


def apply(rom: bytearray, jp_rom: bytes):
    """Repoints the battle fragments and the name lookup of the messages.
    `jp_rom` = original ROM (the name table is read before relocation)."""
    cursor = POOL_FILE
    cache = {}

    def intern(ids):
        nonlocal cursor
        key = tuple(ids)
        if key not in cache:
            if cursor + 2 * len(ids) > POOL_END:
                raise SystemExit("Battle text area $BF overflow.")
            for j, cid in enumerate(ids):
                struct.pack_into("<H", rom, cursor + 2 * j, cid)
            cache[key] = 0x8000 + (cursor - POOL_FILE)
            cursor += 2 * len(ids)
        return cache[key]

    # 1) Parallel name table at the start of the area (3 bytes per entry)
    table_file = cursor
    cursor += 3 * NF.N_ENTRIES
    names = _hw_names(jp_rom)
    for e, text in enumerate(names):
        o = NF.NAME_TBL + 3 * e
        if text is None:
            ptr = rom[o:o + 3]                     # current pointer (relocated or JP)
        else:
            a = intern(encode_hw(text) + [0xFFFF])
            ptr = bytes([a & 0xFF, a >> 8, POOL_BANK])
        rom[table_file + 3 * e:table_file + 3 * e + 3] = ptr
    base = 0x8000 + (table_file - POOL_FILE) - 3   # index 1-based
    for k, o in enumerate(NAME_LOOKUP_OPERANDS):
        if rom[o - 1] != 0xBF or rom[o:o + 3] != bytes([0x58 + k, 0xAF, 0x81]):
            raise SystemExit(f"Unexpected $81:9D19 at 0x{o:06X}")
        a = base + k
        rom[o:o + 3] = bytes([a & 0xFF, a >> 8, POOL_BANK])

    # 2) Fragments: one pointer per site
    for site, jp_target, text in SITES:
        o = lorom(site)
        lo, hi, bk = jp_target & 0xFF, (jp_target >> 8) & 0xFF, jp_target >> 16
        expect = bytes([0xA9, lo, 0x85, 0x09, 0xA9, hi, 0x85, 0x0A, 0xA9, bk, 0x85, 0x0B])
        if rom[o:o + 12] != expect:
            raise SystemExit(f"Unexpected message site at ${site:06X}")
        a = intern(encode_hw(text) + [0xFFFF])
        rom[o + 1] = a & 0xFF
        rom[o + 5] = a >> 8
        rom[o + 9] = POOL_BANK

    # 3) HP HUD: given name, then initial
    for off, old, new in HUD_SWAPS:
        if rom[off:off + len(old)] != old:
            raise SystemExit(f"Unexpected HP HUD at 0x{off:06X}")
        rom[off:off + len(new)] = new

    longest = max(len(t) for t in names if t and not t.startswith(" "))
    return {"sites": len(SITES), "strings": len(cache), "bytes": cursor - POOL_FILE,
            "longest_name": longest}
