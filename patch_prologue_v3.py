#!/usr/bin/env python3
"""
Nage Libre — Full English Translation ROM Builder v6
=====================================================

KEY FIX: Scatter allocator — only uses font IDs whose 64-byte tile data
is blank in the original ROM. NEVER overwrites existing game font data.

VWF: Dual-character encoding (2 English chars per 16×16 tile)
"""
import struct
from pathlib import Path

ROM_PATH = Path(__file__).parent / "Nage Libre - Seijaku no Suishin (Japan).sfc"
PATCHED_PATH = Path(__file__).parent / "Nage Libre - Patched.sfc"

JP_SPACE = 0x03FE

# ---------------------------------------------------------------------------
# 8×8 pixel font (half-width glyphs)
# ---------------------------------------------------------------------------
FONT = {
    'A': ([0x00,0x3C,0x66,0x66,0x66,0x7E,0x66,0x66],[0x00]*8),
    'B': ([0x00,0x7C,0x66,0x7C,0x66,0x66,0x66,0x7C],[0x00]*8),
    'C': ([0x00,0x3C,0x66,0x60,0x60,0x60,0x66,0x3C],[0x00]*8),
    'D': ([0x00,0x78,0x6C,0x66,0x66,0x66,0x6C,0x78],[0x00]*8),
    'E': ([0x00,0x7E,0x60,0x7C,0x60,0x60,0x60,0x7E],[0x00]*8),
    'F': ([0x00,0x7E,0x60,0x7C,0x60,0x60,0x60,0x60],[0x00]*8),
    'G': ([0x00,0x3C,0x66,0x60,0x6E,0x66,0x66,0x3E],[0x00]*8),
    'H': ([0x00,0x66,0x66,0x7E,0x66,0x66,0x66,0x66],[0x00]*8),
    'I': ([0x00,0x3C,0x18,0x18,0x18,0x18,0x18,0x3C],[0x00]*8),
    'J': ([0x00,0x1E,0x06,0x06,0x06,0x06,0x66,0x3C],[0x00]*8),
    'K': ([0x00,0x66,0x6C,0x78,0x78,0x6C,0x66,0x66],[0x00]*8),
    'L': ([0x00,0x60,0x60,0x60,0x60,0x60,0x60,0x7E],[0x00]*8),
    'M': ([0x00,0x63,0x77,0x7F,0x6B,0x63,0x63,0x63],[0x00]*8),
    'N': ([0x00,0x66,0x76,0x7E,0x6E,0x66,0x66,0x66],[0x00]*8),
    'O': ([0x00,0x3C,0x66,0x66,0x66,0x66,0x66,0x3C],[0x00]*8),
    'P': ([0x00,0x7C,0x66,0x66,0x7C,0x60,0x60,0x60],[0x00]*8),
    'Q': ([0x00,0x3C,0x66,0x66,0x66,0x6E,0x3C,0x0E],[0x00]*8),
    'R': ([0x00,0x7C,0x66,0x66,0x7C,0x6C,0x66,0x66],[0x00]*8),
    'S': ([0x00,0x3C,0x66,0x60,0x3C,0x06,0x66,0x3C],[0x00]*8),
    'T': ([0x00,0x7E,0x18,0x18,0x18,0x18,0x18,0x18],[0x00]*8),
    'U': ([0x00,0x66,0x66,0x66,0x66,0x66,0x66,0x3C],[0x00]*8),
    'V': ([0x00,0x66,0x66,0x66,0x66,0x3C,0x3C,0x18],[0x00]*8),
    'W': ([0x00,0x63,0x63,0x63,0x6B,0x7F,0x77,0x63],[0x00]*8),
    'X': ([0x00,0x66,0x66,0x3C,0x18,0x3C,0x66,0x66],[0x00]*8),
    'Y': ([0x00,0x66,0x66,0x3C,0x18,0x18,0x18,0x18],[0x00]*8),
    'Z': ([0x00,0x7E,0x06,0x0C,0x18,0x30,0x60,0x7E],[0x00]*8),
    'a': ([0x00,0x00,0x00,0x3C,0x06,0x3E,0x66,0x3E],[0x00]*8),
    'b': ([0x00,0x60,0x60,0x7C,0x66,0x66,0x66,0x7C],[0x00]*8),
    'c': ([0x00,0x00,0x00,0x3C,0x66,0x60,0x66,0x3C],[0x00]*8),
    'd': ([0x00,0x06,0x06,0x3E,0x66,0x66,0x66,0x3E],[0x00]*8),
    'e': ([0x00,0x00,0x00,0x3C,0x66,0x7E,0x60,0x3C],[0x00]*8),
    'f': ([0x00,0x1C,0x36,0x30,0x7C,0x30,0x30,0x30],[0x00]*8),
    'g': ([0x00,0x00,0x00,0x3E,0x66,0x66,0x3E,0x06],[0x66,0x3C]+[0]*6),
    'h': ([0x00,0x60,0x60,0x7C,0x66,0x66,0x66,0x66],[0x00]*8),
    'i': ([0x00,0x18,0x00,0x38,0x18,0x18,0x18,0x3C],[0x00]*8),
    'j': ([0x00,0x06,0x00,0x0E,0x06,0x06,0x06,0x06],[0x66,0x3C]+[0]*6),
    'k': ([0x00,0x60,0x60,0x66,0x6C,0x78,0x6C,0x66],[0x00]*8),
    'l': ([0x00,0x38,0x18,0x18,0x18,0x18,0x18,0x3C],[0x00]*8),
    'm': ([0x00,0x00,0x00,0x76,0x7F,0x6B,0x63,0x63],[0x00]*8),
    'n': ([0x00,0x00,0x00,0x7C,0x66,0x66,0x66,0x66],[0x00]*8),
    'o': ([0x00,0x00,0x00,0x3C,0x66,0x66,0x66,0x3C],[0x00]*8),
    'p': ([0x00,0x00,0x00,0x7C,0x66,0x66,0x7C,0x60],[0x60,0x60]+[0]*6),
    'q': ([0x00,0x00,0x00,0x3E,0x66,0x66,0x3E,0x06],[0x06,0x06]+[0]*6),
    'r': ([0x00,0x00,0x00,0x6C,0x76,0x60,0x60,0x60],[0x00]*8),
    's': ([0x00,0x00,0x00,0x3E,0x60,0x3C,0x06,0x7C],[0x00]*8),
    't': ([0x00,0x30,0x30,0x7C,0x30,0x30,0x36,0x1C],[0x00]*8),
    'u': ([0x00,0x00,0x00,0x66,0x66,0x66,0x66,0x3E],[0x00]*8),
    'v': ([0x00,0x00,0x00,0x66,0x66,0x66,0x3C,0x18],[0x00]*8),
    'w': ([0x00,0x00,0x00,0x63,0x6B,0x6B,0x7F,0x36],[0x00]*8),
    'x': ([0x00,0x00,0x00,0x66,0x3C,0x18,0x3C,0x66],[0x00]*8),
    'y': ([0x00,0x00,0x00,0x66,0x66,0x66,0x3E,0x06],[0x66,0x3C]+[0]*6),
    'z': ([0x00,0x00,0x00,0x7E,0x0C,0x18,0x30,0x7E],[0x00]*8),
    '0': ([0x00,0x3C,0x66,0x6E,0x76,0x66,0x66,0x3C],[0x00]*8),
    '1': ([0x00,0x18,0x38,0x78,0x18,0x18,0x18,0x7E],[0x00]*8),
    '2': ([0x00,0x3C,0x66,0x06,0x0C,0x18,0x30,0x7E],[0x00]*8),
    '3': ([0x00,0x3C,0x66,0x06,0x1C,0x06,0x66,0x3C],[0x00]*8),
    '4': ([0x00,0x0C,0x1C,0x3C,0x6C,0x7E,0x0C,0x0C],[0x00]*8),
    '5': ([0x00,0x7E,0x60,0x7C,0x06,0x06,0x66,0x3C],[0x00]*8),
    '6': ([0x00,0x3C,0x66,0x60,0x7C,0x66,0x66,0x3C],[0x00]*8),
    '7': ([0x00,0x7E,0x06,0x0C,0x18,0x18,0x18,0x18],[0x00]*8),
    '8': ([0x00,0x3C,0x66,0x66,0x3C,0x66,0x66,0x3C],[0x00]*8),
    '9': ([0x00,0x3C,0x66,0x66,0x3E,0x06,0x66,0x3C],[0x00]*8),
    ' ': ([0x00]*8,[0x00]*8),
    '.': ([0x00,0x00,0x00,0x00,0x00,0x00,0x18,0x18],[0x00]*8),
    ',': ([0x00,0x00,0x00,0x00,0x00,0x00,0x18,0x18],[0x08,0x10]+[0]*6),
    '!': ([0x00,0x18,0x18,0x18,0x18,0x18,0x00,0x18],[0x00]*8),
    '?': ([0x00,0x3C,0x66,0x06,0x0C,0x18,0x00,0x18],[0x00]*8),
    "'": ([0x00,0x18,0x18,0x10,0x00,0x00,0x00,0x00],[0x00]*8),
    '-': ([0x00,0x00,0x00,0x7E,0x00,0x00,0x00,0x00],[0x00]*8),
    '/': ([0x00,0x06,0x0C,0x18,0x30,0x60,0x40,0x00],[0x00]*8),
    '*': ([0x00,0x00,0x66,0x3C,0xFF,0x3C,0x66,0x00],[0x00]*8),
}

# ---------------------------------------------------------------------------
# ROM utilities
# ---------------------------------------------------------------------------
def char_id_to_rom(cid):
    a = ((cid * 32) + 0x8000) & 0xFFFF
    if a >= 0x8000:
        return ((0x85 & 0x7F) * 0x8000) + (a - 0x8000)
    return ((0x86 & 0x7F) * 0x8000) + a

def _rows_to_2bpp(rows):
    tile = bytearray(16)
    for i, p in enumerate(rows):
        tile[i*2] = p       # bp0 = pixel → color 1 = white
        tile[i*2+1] = 0x00  # bp1 = 0
    return bytes(tile)

def make_pair_tile(ch_l, ch_r):
    lt, lb = FONT[ch_l]
    rt, rb = FONT[ch_r]
    return _rows_to_2bpp(lt) + _rows_to_2bpp(lb) + _rows_to_2bpp(rt) + _rows_to_2bpp(rb)

def fix_checksum(rom):
    rom[0x7FDC:0x7FE0] = b'\xFF\xFF\x00\x00'
    cs = sum(rom) & 0xFFFF
    comp = cs ^ 0xFFFF
    struct.pack_into('<HH', rom, 0x7FDC, comp, cs)
    return cs

# ---------------------------------------------------------------------------
# Scatter allocator — picks from verified-safe font IDs only
# ---------------------------------------------------------------------------
def find_safe_ids(rom):
    """Find even character IDs safe for pair tile allocation.
    
    Three tiers (ordered by safety):
    1. Super-safe: both N and N+1 have blank font data AND unreferenced
    2. Semi-safe: N is blank+unreferenced, N+1 has data but unreferenced
    3. Extended: both N and N+1 are unreferenced but may have data.
       Font banks ($85-$86) are dedicated character data, so unreferenced
       IDs with existing graphics (unused kanji) can be safely overwritten.
       Prefer higher IDs (0x0100+) to avoid system/control tiles.
    
    CRITICAL: Some blank IDs (like 0x03FE = space) are actively used by the
    game. We must exclude ALL referenced IDs, not just non-blank ones."""
    
    # Step 1: Find all IDs with blank (all-zero) font data
    blank = set()
    for cid in range(0x0800):
        off = char_id_to_rom(cid)
        if all(b == 0 for b in rom[off:off+64]):
            blank.add(cid)
    
    # Step 2: Collect ALL char IDs referenced anywhere in game text
    referenced = set()
    
    # Bank $87 text table (16-bit IDs)
    i = 0x038697
    while i < 0x038C01:
        w = rom[i] | (rom[i+1] << 8)
        if w != 0xFFFF and w < 0x0800:
            referenced.add(w)
        i += 2
    
    # Always exclude known special IDs
    referenced.add(0x03FE)  # JP_SPACE — blank but critical!
    referenced.add(0x03FF)  # Adjacent to JP_SPACE
    referenced.add(0x02AA)  # Ellipsis (…)
    referenced.add(0x02AB)
    referenced.add(0x02E0)  # Exclamation (‼)
    referenced.add(0x02E1)
    
    # Step 3: Filter by tiers
    # Tier 1: both N and N+1 blank AND neither referenced
    safe = sorted(n for n in blank 
                  if n % 2 == 0 and (n+1) in blank
                  and n not in referenced and (n+1) not in referenced)
    
    # Tier 2: N blank+unreferenced, N+1 has data but not referenced
    semi = sorted(n for n in blank 
                  if n % 2 == 0 and (n+1) not in blank
                  and n not in referenced and (n+1) not in referenced)
    
    # Tier 3: both unreferenced, at least one non-blank (unused kanji)
    # Prefer IDs >= 0x0100 (avoid low system/control tile range)
    tier1_2 = set(safe + semi)
    extended = sorted(n for n in range(0x0100, 0x0800, 2)
                      if n not in tier1_2
                      and n not in referenced and (n+1) not in referenced)
    
    return safe + semi + extended

class ScatterAllocator:
    def __init__(self, free_ids):
        self.free = list(free_ids)
        self.idx = 0
        self.p2id = {}
        self.id2p = {}
    
    def get(self, cl, cr):
        k = (cl, cr)
        if k not in self.p2id:
            if self.idx >= len(self.free):
                raise RuntimeError(
                    f"Out of free font IDs! Used {self.idx}/{len(self.free)}. "
                    f"Reduce translations or find more free IDs.")
            cid = self.free[self.idx]
            self.idx += 1
            self.p2id[k] = cid
            self.id2p[cid] = k
        return self.p2id[k]
    
    def count(self):
        return len(self.p2id)
    
    def available(self):
        return len(self.free) - self.idx

# ---------------------------------------------------------------------------
# Text encoding
# ---------------------------------------------------------------------------
def encode_en(text, alloc):
    ids = []
    chars = list(text)
    i = 0
    while i < len(chars):
        cl = chars[i]
        if cl == '\u2026':  # …
            ids.append(0x02AA)
            i += 1
            continue
        cr = chars[i+1] if i+1 < len(chars) else ' '
        if cr == '\u2026':
            cr = ' '
        elif cr not in FONT:
            cr = ' '
        if cl == ' ' and cr == ' ':
            ids.append(JP_SPACE)
            i += 1                 # consume second space (+ bottom i+=1 = 2 total)
        elif cl not in FONT:
            ids.append(JP_SPACE)
        else:
            ids.append(alloc.get(cl, cr))
            i += 1                 # consume second char  (+ bottom i+=1 = 2 total)
        i += 1                     # consume first char
    return ids

def encode_to_slots(text, slot_count, alloc):
    ids = encode_en(text, alloc)
    while len(ids) < slot_count:
        ids.append(JP_SPACE)
    return ids[:slot_count]

# ---------------------------------------------------------------------------
# TRANSLATION TABLE — Optimized to fit within 163 safe font slots
# ---------------------------------------------------------------------------
BANK87_TRANSLATIONS = {
    # Battle messages (appended to character name)
    4:  "'s pal!",             # の友達‼ (4 IDs=8ch)
    5:  "  ",                  # は (1 ID)
    6:  " damage!!",           # のダメージ‼ (6 IDs=12ch)
    7:  "Healed!",             # 回復した (4 IDs=8ch)
    8:  "ATK up!!",            # 攻撃がアップ‼ (7 IDs=14ch)
    9:  "Pick a card!",        # 入れかえるカードを選んでね (13 IDs=26ch)
    10: "Healing...",          # ただいま若がえ中です… (11 IDs=22ch)
    11: "Run!!",               # 逃げろぉ‼ (5 IDs=10ch)
    12: "Caught!!",            # おいつかれてしまった‼ (12 IDs=24ch)
    13: "Escaped!",            # なんとか、逃げられた… (12 IDs=24ch)
    14: " B.stone",            # 誕生石☆☆ (6 IDs=12ch)
    15: "No effect!!",         # ダメージをあたえられない‼ (13 IDs=26ch)
    16: "Don't go!!",          # 逃げるな待てぇ‼ (9 IDs=18ch)
    17: "Caught up!",          # おいついた (6 IDs=12ch)
    18: "Got away!!",          # 逃げられてしまった (10 IDs=20ch)
    19: " defeated!",          # を倒した‼ (5 IDs=10ch)
    20: "Got GP!!",            # ゴールド手に入れた‼ (10 IDs=20ch)
    21: " went up!!",          # 上がった‼ (5 IDs=10ch)
    
    # Stat names
    22: "HP",                  # 体力が (3 IDs=6ch)
    23: "MP",                  # 魔力が (3 IDs=6ch)
    24: "ATK",                 # 攻撃力が (4 IDs=8ch)
    25: "DEF",                 # 防御力が (4 IDs=8ch)
    26: "SPD",                 # 素早さが (4 IDs=8ch)
    27: "Level",               # レベルが (4 IDs=8ch)
    28: "  ",                  # が (1 ID)
    29: "Available!!",         # 選べるようになった‼ (10 IDs=20ch)
    30: " went up!!",          # に上がった‼ (6 IDs=12ch)
    31: "B.stone",             # 誕生石☆☆ (5 IDs=10ch)
    32: " Yes     No",         # はい  いいえ (8 IDs=16ch)
    33: "'s move!!",           # の必殺の技だ‼ (7 IDs=14ch)
    
    # System prompts
    34: "Data OK?",            # このデータでいいかな？ (11 IDs=22ch)
    35: "File to load?",       # どのファイルをロードする？ (13 IDs=26ch)
    36: "Buy cards",           # カードを買います (13 IDs=26ch)
    37: "Swap party",          # キャラクターを入れかえます (13 IDs=26ch)
    38: "Sell cards",          # カードをうります (13 IDs=26ch)
    39: "No gold!!",           # お金がたりません‼ (12 IDs=24ch)
    40: "Max stock!",          # これ以上買えません (13 IDs=26ch)
    41: "/",                   # 月 (1 ID)
    42: "  ",                  # 日 (1 ID)
    43: "Birthday?",           # 誕生日をおしえてね (9 IDs=18ch)
    44: "B-day OK?",           # これで誕生日はいいかな？ (12 IDs=24ch)
    45: "File to save?",       # どのファイルにセーブする？ (13 IDs=26ch)
    46: "File",                # ファイル (4 IDs=8ch)
    47: "?",                   # ？ (1 ID)
    48: "Delete data?",        # まえのデータをけしますよ (12 IDs=24ch)
    49: "No   OK",             # だめ よい (5 IDs=10ch)
    50: "None",                # なし (2 IDs=4ch)
    
    # Birthstone names (7 IDs=14ch each)
    51: "Garnet",
    52: "Amethyst",
    53: "Aqua",                # Aquamarine shortened to save pairs
    54: "Diamond",
    55: "Emerald",
    56: "M.stone",             # Moonstone shortened
    57: "Ruby",
    58: "Agate",
    59: "Sapphire",
    60: "Opal",
    61: "Topaz",
    62: "Lapis",               # Lapis Lazuli shortened
    
    # Menu items
    63: "What to do?",         # どうしますか？ (7 IDs=14ch)
    64: "Shop",                # 買い物 (3 IDs=6ch)
    65: "Actions",             # 行動選択 (4 IDs=8ch)
    66: "Save",                # セーブ (3 IDs=6ch)
    67: "Start",               # スタート (4 IDs=8ch)
    68: "EX",                  # EX (2 IDs=4ch)
    
    # Item names (6 IDs=12ch each)
    69: "Ri Orb",
    70: "Be Orb",
    71: "Ra Orb",
    72: "Shi Orb",
    73: "O Orb",
    74: "N Orb",
}

# Prologue — each line is 30 tilemap entries (spanning 2 tilemap rows)
# The visible area shows 16 tiles on visual line 1 (entries 0-15) and
# 14 tiles on visual line 2 (entries 16-29).  Entry 15 must be JP_SPACE
# so nothing leaks at the visual line break.
# Line 0 is at fixed WRAM offset 0x0122 (row 4 col 17)
# Lines 1-2 are found at runtime by scanning column 1 of each row
PROLOGUE_LINES = [
    # VL1(0-15): "  In a far world……      "  VL2(16-29): "A voice echoes……"
    '  In a far world\u2026\u2026            A voice echoes\u2026\u2026',
]

PROLOGUE_SLOT_COUNT = 30  # entries per line (16 visual-line-1 + 14 visual-line-2)


# ---------------------------------------------------------------------------
# Pre-dispatch hook — hooks BEFORE F4CA font loader processes tiles
# ---------------------------------------------------------------------------
def assemble_hook(prologue_lines, alloc):
    # Encode all English lines
    # Screen 1 Line 1
    s1_l1 = encode_to_slots('  In a far world\u2026\u2026', 16, alloc)
    # Screen 1 Line 2
    s1_l2 = encode_to_slots('A voice echoes\u2026\u2026', 16, alloc)
    # Screen 1 Line 3 (blank)
    s1_l3 = [JP_SPACE] * 16
    
    # Screen 2 Line 1
    s2_l1 = encode_to_slots("  'This world is mine\u2026\u2026", 16, alloc)
    # Screen 2 Line 2
    s2_l2 = encode_to_slots("  Bring the darkness bearers\u2026\u2026'", 16, alloc)

    # Targets: (Match Word 1, Match Word 2, English Data)
    targets = [
        (0x02DE, 0x01DA, s1_l1),  # 西暦 -> In a far world
        (0x005A, 0x009C, s1_l2),  # 地球 -> A voice echoes
        (0x00D0, 0x0088, s1_l3),  # 残さ -> (blank)
        (0x0088, 0x001C, s2_l1),  # この -> This world is mine
        (0x0144, 0x0114, s2_l2),  # 心に -> Bring the darkness bearers
    ]

    HOOK_SNES_BASE = 0xF8E3

    code = bytearray()
    # 1. Call original decompressor
    code += bytes([0x22, 0xD8, 0xF8, 0x80])   # JSL $80:F8D8

    # 2. Save state
    code += bytes([0x08, 0x8B, 0xC2, 0x30, 0x48, 0xDA, 0x5A]) # PHP, PHB, REP #$30, PHA, PHX, PHY

    # 3. Set DBR = $83
    code += bytes([0xE2, 0x20, 0xA9, 0x83, 0x48, 0xAB, 0xC2, 0x20]) # SEP #$20, LDA #$83, PHA, PLB, REP #$20

    # 4. Scan buffer at $7F:64C0
    # X = offset in buffer (0 to 0x1000)
    
    data_table_refs = []
    
    for t1, t2, eng_data in targets:
        # Check target
        code += bytes([0xA2, 0x00, 0x00])           # LDX #$0000
        loop_start = len(code)
        code += bytes([0xBF, 0xC0, 0x64, 0x7F])     # LDA.l $7F:64C0,X
        code += bytes([0xC9, t1 & 0xFF, (t1 >> 8) & 0xFF]) # CMP #t1
        bne_next = len(code)
        code += bytes([0xD0, 0x00])                 # BNE next_char
        
        # Match word 1! Check word 2.
        code += bytes([0xBF, 0xC2, 0x64, 0x7F])     # LDA.l $7F:64C2,X
        code += bytes([0xC9, t2 & 0xFF, (t2 >> 8) & 0xFF]) # CMP #t2
        bne_next2 = len(code)
        code += bytes([0xD0, 0x00])                 # BNE next_char
        
        # MATCH FOUND! Overwrite with English data!
        code += bytes([0x5A])                       # PHY
        code += bytes([0xA0, 0x00, 0x00])           # LDY #$0000
        copy_loop = len(code)
        data_ref = len(code)

    # BRA done (after screen 1 write)
    code[bra_done_s1 + 1] = (done_pos - (bra_done_s1 + 2)) & 0xFF

    # JSR write_block0
    sub0 = HOOK_SNES_BASE + write_sub_positions[0]
    code[jsr_w0 + 1] = sub0 & 0xFF
    code[jsr_w0 + 2] = (sub0 >> 8) & 0xFF

    # Fix up data table LDA addresses
    for line_idx, data_ref in data_table_positions:
        data_snes = HOOK_SNES_BASE + data_addresses[line_idx]
        code[data_ref + 1] = data_snes & 0xFF
        code[data_ref + 2] = (data_snes >> 8) & 0xFF

    return bytes(code)

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    with open(ROM_PATH, 'rb') as f:
        rom = bytearray(f.read())
    print(f"Original ROM: {len(rom):,} bytes")

    # Step 1: Find safe font IDs
    print("\n--- Step 1: Finding safe font IDs ---")
    safe_ids = find_safe_ids(rom)
    print(f"  Safe font IDs found: {len(safe_ids)}")
    
    alloc = ScatterAllocator(safe_ids)

    # Step 2: Parse original text table
    print("\n--- Step 2: Parsing text table ---")
    TABLE_START, TABLE_END = 0x038697, 0x038C01
    orig = []
    i, line = TABLE_START, 0
    cur, start_off = [], TABLE_START
    while i < TABLE_END:
        w = rom[i] | (rom[i+1] << 8)
        if w == 0xFFFF:
            orig.append({'line': line, 'rom': start_off, 'ids': cur[:]})
            line += 1; cur = []; i += 2; start_off = i
        else:
            cur.append(w); i += 2
    if cur:
        orig.append({'line': line, 'rom': start_off, 'ids': cur[:]})
    print(f"  {len(orig)} strings parsed")

    # Step 3: Encode translations
    print("\n--- Step 3: Encoding translations ---")
    count = 0
    for s in orig:
        ln = s['line']
        if ln in BANK87_TRANSLATIONS:
            s['translated'] = encode_to_slots(
                BANK87_TRANSLATIONS[ln], len(s['ids']), alloc)
            count += 1
    
    # Encode prologue
    for text in PROLOGUE_LINES:
        encode_en(text, alloc)
    
    print(f"  {count} strings translated")
    print(f"  {alloc.count()} unique pairs (of {len(safe_ids)} available)")

    # Step 4: Write pair tiles to ROM
    print("\n--- Step 4: Writing pair tiles ---")
    for (cl, cr), cid in alloc.p2id.items():
        td = make_pair_tile(cl, cr)
        off = char_id_to_rom(cid)
        rom[off:off+64] = td
    print(f"  {alloc.count()} tiles written (scattered across safe IDs)")

    # Step 5: Patch text table
    print("\n--- Step 5: Patching text table ---")
    patched = 0
    for s in orig:
        if 'translated' in s:
            off = s['rom']
            for i, cid in enumerate(s['translated']):
                struct.pack_into('<H', rom, off + i * 2, cid)
            patched += 1
    print(f"  {patched} strings patched")

    for ln in [4, 7, 22, 51, 63, 64]:
        s = orig[ln]
        if 'translated' in s:
            print(f"    Line {ln:2d}: \"{BANK87_TRANSLATIONS[ln]}\"")

    # Step 6: Pre-dispatch hook (hooks BEFORE tilemap type dispatch)
    print("\n--- Step 6: Hook ---")
    hook = assemble_hook(PROLOGUE_LINES, alloc)
    HOOK_ROM, HOOK_BANK, HOOK_ADDR = 0x01F8E3, 0x83, 0xF8E3
    rom[HOOK_ROM:HOOK_ROM + len(hook)] = hook
    # Patch $83:80FF: replace JSL $80:F8D8 with JSL $83:F8E3
    HP = 0x0180FF  # lorom(0x83, 0x80FF)
    rom[HP:HP+4] = bytes([0x22, HOOK_ADDR & 0xFF, (HOOK_ADDR >> 8) & 0xFF, HOOK_BANK])
    print(f"  {len(hook)} bytes, $83:80FF → ${HOOK_BANK:02X}:{HOOK_ADDR:04X}")

    # Step 6b: Direct ROM patch for screen 2 prologue text
    # Screen 2 (clouds) uses a SEPARATE dialogue rendering system:
    #   $87:D63B → $87:DA3B → $80:F4A7
    # F4A7 reads tile IDs from ROM and loads font glyphs + writes tilemap.
    # The text tile IDs are stored at these fixed ROM addresses:
    #   String #7 at $87:89C5 (12 tiles) — line 1 main text
    #   String #18 at $87:8A81 (7 tiles, via $87:8969) — line 2 part A
    #   DA8C entry at $87:8A51 (7 tiles) — additional tiles
    print("\n--- Step 6b: Screen 2 direct ROM patch ---")

    # Encode screen 2 English text as pair tile IDs
    # Line 1: "'This world is mine……" → 12 tiles + 5 tiles for part B
    # To keep it simple, we put the full text in part A, and pad part B with spaces.
    s2_line1_text = " 'This world is mine"
    s2_line1_ids = encode_en(s2_line1_text, alloc)
    while len(s2_line1_ids) < 12:
        s2_line1_ids.append(JP_SPACE)
    s2_line1_ids = s2_line1_ids[:12]

    # Part B (Fuffuffu) -> just spaces, or the closing quote
    s2_line1b_text = "\u2026\u2026'"
    s2_line1b_ids = encode_en(s2_line1b_text, alloc)
    while len(s2_line1b_ids) < 5:
        s2_line1b_ids.append(JP_SPACE)
    s2_line1b_ids = s2_line1b_ids[:5]

    # Line 2: "Bring the darkness bearers……'"
    s2_line2_text = " Bring the darkness bearers\u2026\u2026'"
    s2_line2_ids = encode_en(s2_line2_text, alloc)
    
    # Split across THREE strings: 8A51 (7 tiles), 8A61 (7 tiles), 8A71 (5 tiles)
    s2_line2_a = s2_line2_ids[:7]
    s2_line2_b = s2_line2_ids[7:14]
    s2_line2_c = s2_line2_ids[14:19]
    
    while len(s2_line2_a) < 7: s2_line2_a.append(JP_SPACE)
    while len(s2_line2_b) < 7: s2_line2_b.append(JP_SPACE)
    while len(s2_line2_c) < 5: s2_line2_c.append(JP_SPACE)

    # Patch line 1 part A at $87:89C5 (12 tiles)
    off_s1a = 0x0389C5
    for i, cid in enumerate(s2_line1_ids):
        struct.pack_into('<H', rom, off_s1a + i * 2, cid)
    print(f"  Line 1A at $87:89C5: {len(s2_line1_ids)} tiles → \"{s2_line1_text}\"")

    # Patch line 1 part B at $87:89DF (5 tiles)
    off_s1b = 0x0389DF
    for i, cid in enumerate(s2_line1b_ids):
        struct.pack_into('<H', rom, off_s1b + i * 2, cid)
    print(f"  Line 1B at $87:89DF: {len(s2_line1b_ids)} tiles → \"{s2_line1b_text}\"")

    # Patch line 2 part A at $87:8A51 (7 tiles)
    off_s2a = 0x038A51
    for i, cid in enumerate(s2_line2_a):
        struct.pack_into('<H', rom, off_s2a + i * 2, cid)
    print(f"  Line 2A at $87:8A51: {len(s2_line2_a)} tiles")

    # Patch line 2 part B at $87:8A61 (7 tiles)
    off_s2b = 0x038A61
    for i, cid in enumerate(s2_line2_b):
        struct.pack_into('<H', rom, off_s2b + i * 2, cid)
    print(f"  Line 2B at $87:8A61: {len(s2_line2_b)} tiles")

    # Patch line 2 part C at $87:8A71 (5 tiles)
    off_s2c = 0x038A71
    for i, cid in enumerate(s2_line2_c):
        struct.pack_into('<H', rom, off_s2c + i * 2, cid)
    print(f"  Line 2C at $87:8A71: {len(s2_line2_c)} tiles")

    # Step 7: Finalize
    print("\n--- Step 7: Finalize ---")
    cs = fix_checksum(rom)
    print(f"  Checksum: ${cs:04X}")
    with open(PATCHED_PATH, 'wb') as f:
        f.write(rom)
    print(f"\n{'='*60}")
    print(f"  Patched ROM: {PATCHED_PATH}")
    print(f"  {alloc.count()} pairs in {len(safe_ids)} safe slots")
    print(f"  Original font data: UNTOUCHED")
    print(f"{'='*60}")

if __name__ == '__main__':
    main()
