#!/usr/bin/env python3
"""
Analyse un dump Mesen produit par scripts/mesen_prologue_dump.lua.

Usage:
  python3 scripts/analyze_mesen_dump.py mesen_dumps/20260519_143022_PC_0087DCCB_001
  python3 scripts/analyze_mesen_dump.py mesen_dumps/   # tous les dumps
"""
from __future__ import annotations

import struct
import sys
from pathlib import Path

# IDs connus (prologue + ponctuation)
GLYPH = {
    0x0010: "あ", 0x002A: "く", 0x005A: "で", 0x0088: "ほ", 0x009C: "球",
    0x02AA: "…", 0x02DE: "西", 0x01DA: "暦", 0x03FE: " ",
    0x075A: "遠", 0x070E: "声", 0x04BE: "響",
}
SPECIAL = {0xFFFF: "[END]", 0x03FE: "SP"}


def read_meta(dump_dir: Path) -> dict[str, str]:
    meta = {}
    p = dump_dir / "meta.txt"
    if not p.is_file():
        return meta
    for line in p.read_text().splitlines():
        if " = " in line:
            k, v = line.split(" = ", 1)
            meta[k.strip()] = v.strip()
    return meta


def words_at(data: bytes, base: int, off: int, count: int) -> list[int]:
    start = off
    out = []
    for i in range(count):
        pos = start + i * 2
        if pos + 2 > len(data):
            break
        out.append(struct.unpack_from("<H", data, pos)[0])
    return out


def dec(ids: list[int]) -> str:
    parts = []
    for cid in ids:
        if cid in SPECIAL:
            parts.append(SPECIAL[cid])
        elif cid in GLYPH:
            parts.append(GLYPH[cid])
        elif cid == 0:
            parts.append("·")
        else:
            parts.append(f"[{cid:04X}]")
    return "".join(parts)


def analyze_dump(dump_dir: Path) -> None:
    print("=" * 72)
    print(dump_dir.name)
    meta = read_meta(dump_dir)
    for k in ("reason", "pc", "frame", "rom", "a", "x", "y"):
        if k in meta:
            print(f"  {k}: {meta[k]}")

    tilemap = dump_dir / "wram_7F6000_1000.bin"
    if not tilemap.is_file():
        print("  (pas de wram_7F6000_1000.bin)")
        return

    data = tilemap.read_bytes()
    # offsets depuis $7F:64C0 → index dans bin = addr - 0x7F6000
    base_addr = 0x7F6000
    tilemap_base = 0x7F64C0
    rel_base = tilemap_base - base_addr

    regions = [
        (0x0122, "L1 visible ($65E2)", 16),
        (0x0142, "signature/L2 ($6602)", 14),
        (0x01A2, "row2 ($6662)", 16),
        (0x0222, "row3 preload ($66E2)", 16),
    ]

    for off, label, count in regions:
        pos = rel_base + off
        ids = words_at(data, base_addr, pos, count)
        print(f"\n  --- {label} (+${off:04X}) ---")
        print(f"  IDs: {' '.join(f'{w:04X}' for w in ids)}")
        print(f"  JP-ish: {dec(ids)}")

    sig = words_at(data, base_addr, rel_base + 0x0142, 2)
    if len(sig) >= 2:
        ok = sig[0] == 0x075A and sig[1] == 0x002A
        print(f"\n  Signature 075A+002A: {'OK' if ok else 'non'} ({sig[0]:04X} {sig[1]:04X})")

    zp = dump_dir / "zp_direct.txt"
    if zp.is_file():
        print(f"\n  --- zp_direct.txt (extrait) ---")
        for line in zp.read_text().splitlines()[:12]:
            print(f"  {line}")


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: analyze_mesen_dump.py <dump_dir|mesen_dumps/>", file=sys.stderr)
        sys.exit(1)

    target = Path(sys.argv[1])
    if target.is_dir() and (target / "meta.txt").is_file():
        analyze_dump(target)
        return

    if target.is_dir():
        dumps = sorted(p for p in target.iterdir() if p.is_dir() and (p / "meta.txt").is_file())
        if not dumps:
            print(f"Aucun dump dans {target}", file=sys.stderr)
            sys.exit(1)
        for d in dumps:
            analyze_dump(d)
        return

    print(f"Chemin invalide: {target}", file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    main()
