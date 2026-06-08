#!/usr/bin/env python3
"""Decode a Bank $87 prologue/UI string (16-bit tile IDs, LE, terminated by FFFF)."""
import struct
import sys
from pathlib import Path

ROM = Path(__file__).resolve().parent.parent / "Nage Libre - Seijaku no Suishin (Japan).sfc"

# Mapping confirmé (prologue + UI) — voir docs/prologue_text_engine.md
CHARS: dict[int, str] = {
    0x0010: "あ", 0x0014: "い", 0x0018: "う", 0x001A: "ぇ", 0x001C: "の", 0x001E: "ぉ",
    0x0020: "お", 0x0022: "か", 0x0024: "が", 0x002A: "く", 0x002E: "私", 0x0030: "げ",
    0x0032: "こ", 0x0036: "さ", 0x003A: "の", 0x003E: "に", 0x0042: "せ", 0x004A: "た",
    0x004C: "心", 0x0052: "っ", 0x0054: "つ", 0x0058: "て", 0x005A: "地", 0x005C: "と",
    0x005E: "ど", 0x0060: "な", 0x0062: "に", 0x0066: "ね", 0x0068: "世", 0x006A: "は",
    0x007E: "べ", 0x0088: "物", 0x008E: "に", 0x0092: "を", 0x009E: "…", 0x00A2: "ら",
    0x00A4: "り", 0x00A6: "る", 0x00A8: "れ", 0x00AA: "ろ", 0x00AE: "て", 0x00B0: "ん",
    0x00B2: "ア", 0x00B6: "イ", 0x00BE: "エ", 0x00C2: "オ", 0x00C4: "カ", 0x00C6: "ガ",
    0x00C8: "キ", 0x00CC: "ク", 0x00D6: "ゴ", 0x00D8: "集", 0x00DC: "シ", 0x00DE: "ジ",
    0x00E0: "ス", 0x00E4: "セ", 0x00EC: "全", 0x00EE: "ダ", 0x00F4: "ツ", 0x00FC: "界",
    0x00FE: "ト", 0x0100: "ド", 0x0114: "達", 0x0118: "フ", 0x011A: "ブ", 0x0144: "者",
    0x0156: "え", 0x01DA: "暦", 0x02C8: "…", 0x02DE: "西", 0x033A: "世", 0x033C: "界",
    0x04BE: "響", 0x070E: "声", 0x075A: "遠", 0x0014: "闇",
    0x03FE: " ", 0x02AA: "…", 0x02FE: "…", 0x02E0: "‼", 0x0346: "　",
}


def lorom(bank: int, addr: int) -> int:
    return ((bank & 0x7F) * 0x8000) + (addr - 0x8000)


def read_string(rom: bytes, bank: int, addr: int, max_words: int = 80) -> list[int]:
    off = lorom(bank, addr)
    ids: list[int] = []
    for _ in range(max_words):
        w = struct.unpack_from("<H", rom, off + len(ids) * 2)[0]
        if w == 0xFFFF:
            break
        ids.append(w)
    return ids


def decode(ids: list[int]) -> str:
    return "".join(CHARS.get(i, f"[{i:04X}]") for i in ids)


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: decode_bank87_string.py 89C5 [89DF 8A51 ...]")
        sys.exit(1)

    rom = ROM.read_bytes()
    for arg in sys.argv[1:]:
        addr = int(arg, 16)
        ids = read_string(rom, 0x87, addr)
        print(f"$87:{addr:04X}  ({len(ids)} mots)")
        print(f"  IDs: {' '.join(f'{x:04X}' for x in ids)}")
        print(f"  JP:  {decode(ids)}")


if __name__ == "__main__":
    main()
