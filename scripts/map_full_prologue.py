#!/usr/bin/env python3
"""Map full New Game prologue: driver flow, string pointers, WRAM signatures."""
import csv
import struct
from pathlib import Path

ROM_PATH = Path(__file__).parent.parent / "Nage Libre - Seijaku no Suishin (Japan).sfc"

# Confirmed mappings from extracted_scripts.csv + patch_rom + decode_strings
GLYPH = {
    0x0010: "あ", 0x0014: "い", 0x0018: "う", 0x001A: "ぇ", 0x001C: "え", 0x001E: "ぉ",
    0x0020: "お", 0x0022: "か", 0x0024: "が", 0x002A: "く", 0x002E: "け", 0x0030: "げ",
    0x0032: "こ", 0x0036: "さ", 0x003A: "し", 0x003E: "す", 0x0042: "せ", 0x004A: "た",
    0x004C: "だ", 0x0052: "っ", 0x0054: "つ", 0x0058: "て", 0x005A: "で", 0x005C: "と",
    0x005E: "ど", 0x0060: "な", 0x0062: "に", 0x0066: "ね", 0x0068: "の", 0x006A: "は",
    0x007E: "べ", 0x0088: "ほ", 0x008E: "め", 0x0092: "を", 0x009E: "よ", 0x00A2: "ら",
    0x00A4: "り", 0x00A6: "る", 0x00A8: "れ", 0x00AA: "ろ", 0x00AE: "を", 0x00B0: "ん",
    0x00B2: "ア", 0x00B6: "イ", 0x00BE: "エ", 0x00C2: "オ", 0x00C4: "カ", 0x00C6: "ガ",
    0x00C8: "キ", 0x00CC: "ク", 0x00D6: "ゴ", 0x00D8: "サ", 0x00DC: "シ", 0x00DE: "ジ",
    0x00E0: "ス", 0x00E4: "セ", 0x00EC: "タ", 0x00EE: "ダ", 0x00F4: "ツ", 0x00FC: "デ",
    0x00FE: "ト", 0x0100: "ド", 0x0108: "ネ", 0x0110: "パ", 0x0114: "ビ", 0x0116: "ピ",
    0x0118: "フ", 0x011A: "ブ", 0x011C: "プ", 0x0120: "ベ", 0x012A: "マ", 0x012E: "ム",
    0x0130: "メ", 0x0132: "モ", 0x0136: "ヤ", 0x0140: "ラ", 0x0142: "リ", 0x0144: "ル",
    0x0146: "レ", 0x0148: "ロ", 0x014E: "ン", 0x0156: "ァ", 0x01DA: "暦", 0x01E4: "ル",
    0x02AA: "…", 0x02C8: "日", 0x02DE: "西", 0x02F4: "ー", 0x033A: "世", 0x033C: "界",
    0x0346: "　", 0x03FE: " ", 0x004C: "心", 0x008E: "闇", 0x00D8: "集", 0x070E: "声",
    0x075A: "遠", 0x04BE: "響", 0x0144: "者", 0x0114: "達", 0x002E: "私", 0x00EC: "全",
    0x0088: "こ", 0x001C: "の", 0x0068: "世", 0x00FC: "界", 0x0092: "を", 0x00AE: "て",
    0x003A: "し", 0x003E: "に", 0x009E: "よ", 0x005A: "地", 0x009C: "球", 0x00D0: "残",
    0x0144: "者", 0x0114: "達", 0x0014: "い", 0x0022: "か", 0x0060: "な",
}
SPECIAL = {0x02AA: "…", 0x02C8: "…", 0x03FE: " ", 0x0346: "　", 0xFFFF: "[END]"}


def lorom(bank: int, addr: int) -> int:
    return ((bank & 0x7F) * 0x8000) + (addr - 0x8000)


def read_words(rom: bytes, bank: int, addr: int, maxw: int = 120) -> list[int]:
    off = lorom(bank, addr)
    ids = []
    for i in range(maxw):
        w = struct.unpack_from("<H", rom, off + i * 2)[0]
        if w == 0xFFFF:
            break
        ids.append(w)
    return ids


def decode(ids: list[int]) -> str:
    return "".join(SPECIAL.get(i, GLYPH.get(i, f"[{i:04X}]")) for i in ids)


def parse_ld24_before_f4a7(rom: bytes, call_off: int) -> int | None:
    """Find LDA #imm; STA $09/$0A/$0B triple ending in JSL $80F4A7."""
    start = max(0, call_off - 40)
    chunk = rom[start : call_off + 4]
    rel = len(chunk) - 4
    if chunk[rel : rel + 4] != bytes([0x22, 0xA7, 0xF4, 0x80]):
        return None
    # walk backwards for STA $0B, $0A, $0B after LDA #imm
    vals = {}
    i = rel - 1
    while i >= 2:
        if chunk[i] == 0x85 and chunk[i - 1] == 0xA9:
            reg = chunk[i + 1] if i + 1 < len(chunk) else None
            if reg in (0x09, 0x0A, 0x0B):
                vals[reg] = chunk[i]
            i -= 2
            continue
        if chunk[i] == 0x85 and i >= 2 and chunk[i - 2] == 0xA9:
            reg = chunk[i + 1] if i + 1 < len(chunk) else None
            if reg in (0x09, 0x0A, 0x0B) and reg not in vals:
                vals[reg] = chunk[i - 1]
            i -= 3
            continue
        i -= 1
    if {0x09, 0x0A, 0x0B} <= vals.keys():
        return (vals[0x0B] << 16) | (vals[0x0A] << 8) | vals[0x09]
    # alternate: LDA #$xx; STA $09 etc with REP/SEP
    regs = {}
    i = rel - 1
    while i >= 1:
        if chunk[i - 1] == 0xA9:
            imm = chunk[i]
            if i + 2 < len(chunk) and chunk[i + 1] == 0x85:
                reg = chunk[i + 2]
                if reg in (0x09, 0x0A, 0x0B):
                    regs[reg] = imm
            i -= 2
            continue
        i -= 1
    if {0x09, 0x0A, 0x0B} <= regs.keys():
        return (regs[0x0B] << 16) | (regs[0x0A] << 8) | regs[0x09]
    return None


def main():
    rom = ROM_PATH.read_bytes()
    base = lorom(0x87, 0xD63B)
    end = lorom(0x87, 0xEC20)
    chunk = rom[base:end]

    print("=" * 70)
    print("PROLOGUE DRIVER $87:D63B — F4A7 string loads")
    print("=" * 70)

    f4_calls = []
    for i in range(len(chunk) - 4):
        if chunk[i : i + 4] == bytes([0x22, 0xA7, 0xF4, 0x80]):
            site = 0x87D63B + i
            ptr = parse_ld24_before_f4a7(rom, base + i)
            f4_calls.append((site, ptr))

    seen = set()
    for site, ptr in f4_calls:
        if ptr is None or ptr in seen:
            continue
        seen.add(ptr)
        bank, addr = ptr >> 16, ptr & 0xFFFF
        if bank != 0x87 or not (0x8800 <= addr <= 0x8C00):
            continue
        ids = read_words(rom, bank, addr)
        print(f"\n${site:06X}  →  ${ptr:06X}  ({len(ids)} words)")
        print(f"  JP: {decode(ids)}")
        print(f"  IDs: {' '.join(f'{x:04X}' for x in ids)}")

    print("\n" + "=" * 70)
    print("WRAM TILEMAP SIGNATURES (from patch_prologue_v3 targets)")
    print("=" * 70)
    targets = [
        ("075A", "002A", "Screen1 opening 遠く"),
        ("02DE", "01DA", "Screen3? 西暦 narrative L1"),
        ("005A", "009C", "Screen3? 地球 narrative L2"),
        ("00D0", "0088", "Blank / transition"),
        ("0088", "001C", "Screen2 clouds L1 この"),
        ("0144", "0114", "Screen2 clouds L2 心に"),
    ]
    for w1, w2, label in targets:
        print(f"  {w1} {w2} — {label}")

    print("\n" + "=" * 70)
    print("SEARCH: strings starting with よ + ー + し (screen 4?)")
    print("=" * 70)
    for addr in range(0x8800, 0x8C00, 2):
        ids = read_words(rom, 0x87, addr, maxw=16)
        if not ids:
            continue
        text = decode(ids)
        raw = " ".join(f"{x:04X}" for x in ids[:8])
        if text.startswith("よ") and "し" in text[:6]:
            print(f"  $87:{addr:04X}: {text}")
            print(f"    {raw}")
        # also よー pattern
        if len(ids) >= 3 and ids[0] == 0x009E and ids[1] in (0x02F4, 0x00FE, 0x02AA) and ids[2] == 0x003A:
            print(f"  $87:{addr:04X}: {text}  [よーし candidate]")
            print(f"    {raw}")

    print("\n" + "=" * 70)
    print("SEARCH: 西暦 / AM-like digit runs in $87:8800-8C00")
    print("=" * 70)
    for addr in range(0x8800, 0x8C00, 2):
        ids = read_words(rom, 0x87, addr, maxw=24)
        if len(ids) >= 2 and ids[0] == 0x02DE and ids[1] == 0x01DA:
            print(f"  $87:{addr:04X}: {decode(ids)}")
            print(f"    {' '.join(f'{x:04X}' for x in ids)}")

    print("\n" + "=" * 70)
    print("DECOMPRESS SCENE PHASES $83:8103 (counter $06 = 1..7)")
    print("=" * 70)
    handlers = {
        1: 0x8383EE, 2: 0x83849A, 3: 0x8384F5, 4: 0x83856C,
        5: 0x838579, 6: 0x83859C, 7: 0x8385B9,
    }
    for phase, addr in handlers.items():
        print(f"  Phase {phase}: ${addr:06X}")

    # Load extracted_scripts prologue-relevant
    print("\n" + "=" * 70)
    print("extracted_scripts.csv — $87:88xx-$8Axx strings")
    print("=" * 70)
    csv_path = Path(__file__).parent.parent / "docs/extracted_scripts.csv"
    with csv_path.open() as f:
        for row in csv.DictReader(f):
            addr_s = row.get("String Address", "")
            if not addr_s.startswith("$87:8"):
                continue
            a = int(addr_s.split(":")[1], 16)
            if 0x8800 <= a <= 0x8B00:
                ids = [int(x, 16) for x in row["Hex IDs"].split()]
                if len(ids) >= 4:
                    print(f"  {addr_s}  {row['Translated Text'][:50]}")


if __name__ == "__main__":
    main()
