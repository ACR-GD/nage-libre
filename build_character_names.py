#!/usr/bin/env python3
"""
Translation of the character NAMES (Nage Libre).

The $80:F4A7 engine shows character names through the 24-bit pointer tables:
    $81:AF5B  SURNAME table      (entries 0..4 = main players)
    $81:B087  GIVEN NAME table   (entries 100..104 = main players)

In battle and on the birthday screen:
- The top HUD shows the given name, then the surname initial:
  "Ayaka S.", "Mai H.", "Yui K.", "Miki S.", "Ryoko A." (max 8 chars, fits in the 10-wide box).
- The action messages at the bottom (e.g. "Yui hits!!") call JSR $9D19 with the given-name index
  (100 + char_idx). So the given names must be in GIVEN_TBL ($81:B087).
- The order table at $87:DB2C (0x03DB2C) is swapped to show Given name, then Surname initial.

Characters (table order):
    0 桜井彩香  1 姫ノ木舞  2 霧島惟  3 静本美姫  4 葵嶺子
"""
from pathlib import Path

from patch_prologue_v3 import JP_SPACE, encode_en, _rows_to_2bpp

ROOT = Path(__file__).parent

# 24-bit pointer tables (file offsets)
SURNAME_TBL = 0x0AF5B          # $81:AF5B
GIVEN_TBL = 0x0B087            # $81:B087
N_CHARS = 5

# Name display order table (player battle HUD and birthday screen)
# Original format: 01 65 02 66 03 67 04 68 05 69 (Surname, Given name)
# Swapped:         65 01 66 02 67 03 68 04 69 05 (Given name, Surname)
PLAYER_NAME_ORDER_FILE = 0x03DB2C
PLAYER_NAME_ORDER = bytes([0x65, 0x01, 0x66, 0x02, 0x67, 0x03, 0x68, 0x04, 0x69, 0x05])

# Free area in bank $87 for the relocated strings
DATA_FILE = 0x03FA0C           # $87:FA0C
DATA_BANK = 0x87
DATA_ADDR = 0xFA0C             # 16-bit address within the bank
DATA_END = 0x03FFF0            # margin before the end of the bank

# Birthday date "N月 N日": single-glyph strings pointed to by the code.
DATE_MONTH_FILE = 0x038965     # $87:8965  (月, ID 32C)
DATE_DAY_FILE = 0x038969       # $87:8969  (日, ID 2C8)

# Names of the 5 heroines: (Given name, Surname initial)
# For Miki (even length, 4 chars), the initial takes a leading space " S." (2 tiles).
# For Ayaka/Mai/Yui/Ryoko (odd lengths, 3 or 5 chars), the last tile already has a built-in
# space, so the initial is "S." / "H." / "K." / "A." (1 tile).
MAIN_PLAYERS = [
    ("Ayaka", "S."),      # 桜井彩香  (Ay-ak-a␣ + S.  = Ayaka S., 4 tiles)
    ("Mai", "H."),        # 姫ノ木舞  (Ma-i␣    + H.  = Mai H.,   3 tiles)
    ("Yui", "K."),        # 霧島惟    (Yu-i␣    + K.  = Yui K.,   3 tiles)
    ("Miki", " S."),      # 静本美姫  (Mi-ki    + ␣S-.␣ = Miki S., 4 tiles)
    ("Ryoko", "A."),      # 葵嶺子    (Ry-ok-o␣ + A.  = Ryoko A., 4 tiles)
]


def _write_ptr(rom, tbl_file, idx, bank, addr):
    a = tbl_file + idx * 3
    rom[a] = addr & 0xFF
    rom[a + 1] = (addr >> 8) & 0xFF
    rom[a + 2] = bank & 0xFF


def make_slash16():
    """Solid 16×16 (2bpp) "/" glyph, for the date separator between the
    large digits. Diagonal from bottom-left → top-right, ~3px wide.
    Return format: 64 bytes = sub-tiles lt, lb, rt, rb (see make_pair_tile)."""
    grid = [0] * 16                       # 16 lines, bit15 = column 0 (left)
    for r in range(16):
        center = 15 - r                   # slope 1
        for dc in (-1, 0, 1):             # 3px wide
            c = center + dc
            if 0 <= c <= 15:
                grid[r] |= 1 << (15 - c)
    def sub(rows, hi):
        out = []
        for r in rows:
            out.append((grid[r] >> 8) & 0xFF if hi else grid[r] & 0xFF)
        return out
    lt = sub(range(0, 8), hi=True)        # top-left
    lb = sub(range(8, 16), hi=True)       # bottom-left
    rt = sub(range(0, 8), hi=False)       # top-right
    rb = sub(range(8, 16), hi=False)      # bottom-right
    return (_rows_to_2bpp(lt) + _rows_to_2bpp(lb)
            + _rows_to_2bpp(rt) + _rows_to_2bpp(rb))


def apply(rom: bytearray, alloc):
    """Encodes the given names and initials, writes the order table and repoints GIVEN_TBL and SURNAME_TBL."""
    if len(MAIN_PLAYERS) != N_CHARS:
        raise SystemExit(f"MAIN_PLAYERS must contain {N_CHARS} entries.")

    # 1. Swap the display order (given name first, surname initial second)
    rom[PLAYER_NAME_ORDER_FILE:PLAYER_NAME_ORDER_FILE + len(PLAYER_NAME_ORDER)] = PLAYER_NAME_ORDER

    cursor = DATA_FILE
    written = []

    for i, (given, surname_init) in enumerate(MAIN_PLAYERS):
        # Encode given name -> GIVEN_TBL ($81:B087)
        g_ids = encode_en(given, alloc)
        while len(g_ids) > 1 and g_ids[-1] == JP_SPACE:
            g_ids.pop()
        g_ids = g_ids + [0xFFFF]
        g_addr = DATA_ADDR + (cursor - DATA_FILE)
        if cursor + len(g_ids) * 2 > DATA_END:
            raise SystemExit("Free area $87:FA0C overflow for the names.")
        for j, cid in enumerate(g_ids):
            rom[cursor + j * 2] = cid & 0xFF
            rom[cursor + j * 2 + 1] = (cid >> 8) & 0xFF
        cursor += len(g_ids) * 2
        _write_ptr(rom, GIVEN_TBL, i, DATA_BANK, g_addr)

        # Encode surname initial -> SURNAME_TBL ($81:AF5B)
        s_ids = encode_en(surname_init, alloc)
        while len(s_ids) > 1 and s_ids[-1] == JP_SPACE:
            s_ids.pop()
        s_ids = s_ids + [0xFFFF]
        s_addr = DATA_ADDR + (cursor - DATA_FILE)
        if cursor + len(s_ids) * 2 > DATA_END:
            raise SystemExit("Free area $87:FA0C overflow for the names.")
        for j, cid in enumerate(s_ids):
            rom[cursor + j * 2] = cid & 0xFF
            rom[cursor + j * 2 + 1] = (cid >> 8) & 0xFF
        cursor += len(s_ids) * 2
        _write_ptr(rom, SURNAME_TBL, i, DATA_BANK, s_addr)

        written.append((f"{given} {surname_init.strip()}", g_addr, len(g_ids) + len(s_ids)))

    # Date "N月 N日" → "N / N": a dedicated 16×16 "/" glyph in the month cell.
    slash_cid = alloc.get("/", "/")          # reserved ID (rewritten as a 16×16 glyph)
    rom[DATE_MONTH_FILE] = slash_cid & 0xFF
    rom[DATE_MONTH_FILE + 1] = (slash_cid >> 8) & 0xFF
    rom[DATE_DAY_FILE] = 0xFF                  # 日 → empty string
    rom[DATE_DAY_FILE + 1] = 0xFF

    return written, slash_cid, make_slash16()

