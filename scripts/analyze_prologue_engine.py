#!/usr/bin/env python3
"""Static ROM analysis: prologue text, WRAM $7F:64C0, F8DC decompressor."""
import struct
import re
from pathlib import Path

ROM = Path(__file__).resolve().parent.parent / "Nage Libre - Seijaku no Suishin (Japan).sfc"


def lorom(bank: int, addr: int) -> int:
    return ((bank & 0x7F) * 0x8000) + (addr - 0x8000)


def snes_addr(bank: int, offset: int) -> int:
    return (bank << 16) | offset


def disasm_65816(data: bytes, base_snes: int, count: int = 40) -> list[str]:
    """Minimal disassembler for common opcodes (debug aid)."""
    lines = []
    i = 0
    while i < len(data) and len(lines) < count:
        b = data[i]
        snes = base_snes + i
        if b == 0x22 and i + 3 < len(data):
            lo, hi, bk = data[i + 1], data[i + 2], data[i + 3]
            lines.append(f"  ${snes:06X}: JSL ${bk:02X}{hi:02X}{lo:02X}")
            i += 4
        elif b == 0x20 and i + 2 < len(data):
            lo, hi = data[i + 1], data[i + 2]
            lines.append(f"  ${snes:06X}: JSR ${(base_snes >> 16):02X}{hi:02X}{lo:02X}")
            i += 3
        elif b == 0x6B:
            lines.append(f"  ${snes:06X}: RTL")
            i += 1
        elif b == 0x60:
            lines.append(f"  ${snes:06X}: RTS")
            i += 1
        elif b == 0xAF and i + 4 < len(data):
            lo, hi, bk = data[i + 1], data[i + 2], data[i + 3]
            lines.append(f"  ${snes:06X}: LDA.l ${bk:02X}{hi:02X}{lo:02X}")
            i += 5
        elif b == 0x8F and i + 4 < len(data):
            lo, hi, bk = data[i + 1], data[i + 2], data[i + 3]
            lines.append(f"  ${snes:06X}: STA.l ${bk:02X}{hi:02X}{lo:02X}")
            i += 5
        elif b == 0xBF and i + 4 < len(data):
            lo, hi, bk = data[i + 1], data[i + 2], data[i + 3]
            lines.append(f"  ${snes:06X}: LDA.l ${bk:02X}{hi:02X}{lo:02X},X")
            i += 5
        elif b == 0x9F and i + 4 < len(data):
            lo, hi, bk = data[i + 1], data[i + 2], data[i + 3]
            lines.append(f"  ${snes:06X}: STA.l ${bk:02X}{hi:02X}{lo:02X},X")
            i += 5
        elif b == 0xC2 and i + 1 < len(data):
            lines.append(f"  ${snes:06X}: REP #${data[i+1]:02X}")
            i += 2
        elif b == 0xE2 and i + 1 < len(data):
            lines.append(f"  ${snes:06X}: SEP #${data[i+1]:02X}")
            i += 2
        elif b == 0xA2 and i + 2 < len(data):
            lo, hi = data[i + 1], data[i + 2]
            lines.append(f"  ${snes:06X}: LDX #${hi:02X}{lo:02X}")
            i += 3
        elif b == 0xA9 and i + 2 < len(data):
            lo, hi = data[i + 1], data[i + 2]
            lines.append(f"  ${snes:06X}: LDA #${hi:02X}{lo:02X}")
            i += 3
        elif b == 0xC9 and i + 2 < len(data):
            lo, hi = data[i + 1], data[i + 2]
            lines.append(f"  ${snes:06X}: CMP #${hi:02X}{lo:02X}")
            i += 3
        elif b in (0x48, 0x68, 0x08, 0x28, 0xDA, 0xFA, 0x5A, 0x7A):
            names = {0x48: "PHA", 0x68: "PLA", 0x08: "PHP", 0x28: "PLP",
                     0xDA: "PHX", 0xFA: "PLX", 0x5A: "PHY", 0x7A: "PLY"}
            lines.append(f"  ${snes:06X}: {names[b]}")
            i += 1
        else:
            lines.append(f"  ${snes:06X}: ${b:02X}")
            i += 1
    return lines


def scan_abs24(rom: bytes, addr24: int) -> list[int]:
    """Find SNES abs24 byte patterns (LE addr + bank)."""
    pat = bytes([addr24 & 0xFF, (addr24 >> 8) & 0xFF, (addr24 >> 16) & 0xFF])
    hits = []
    start = 0
    while True:
        i = rom.find(pat, start)
        if i < 0:
            break
        hits.append(i)
        start = i + 1
    return hits


def scan_imm16(rom: bytes, val: int) -> list[int]:
    pat = struct.pack("<H", val)
    hits = []
    start = 0
    while True:
        i = rom.find(pat, start)
        if i < 0:
            break
        hits.append(i)
        start = i + 1
    return hits


def rom_to_snes(rom_off: int) -> int:
    bank = (rom_off // 0x8000) + 0x80
    addr = 0x8000 + (rom_off % 0x8000)
    return (bank << 16) | addr


def main():
    rom = ROM.read_bytes()
    print("=== Nage Libre prologue engine — static analysis ===\n")

    # --- F8D8 / F8DC ---
    for label, snes in [("F8D8 wrapper", 0x80F8D8), ("F8DC decompress", 0x80F8DC)]:
        off = lorom(snes >> 16, snes & 0xFFFF)
        chunk = rom[off : off + 128]
        print(f"--- ${snes:06X} ({label}) ---")
        for line in disasm_65816(chunk, snes, 25):
            print(line)
        print()

    # --- Hook site 83:80FF ---
    off = lorom(0x83, 0x80FF)
    print("--- $83:80FF (scene decompress call site) ---")
    for line in disasm_65816(rom[off : off + 64], 0x8380FF, 20):
        print(line)
    print()

    # --- WRAM $7F:64C0 references ---
    print("--- ROM references to WRAM $7F:64C0 (STA/LDA.l ,X) ---")
    for rom_off in scan_abs24(rom, 0x7F64C0)[:30]:
        ctx = rom[max(0, rom_off - 3) : rom_off + 6]
        print(f"  ROM ${rom_off:06X} / SNES ${rom_to_snes(rom_off):06X}: ...{ctx.hex()}...")

    print("\n--- ROM references to WRAM $7F:6602 ---")
    for rom_off in scan_abs24(rom, 0x7F6602)[:20]:
        ctx = rom[max(0, rom_off - 3) : rom_off + 6]
        print(f"  ROM ${rom_off:06X} / SNES ${rom_to_snes(rom_off):06X}: ...{ctx.hex()}...")

    # --- Offset constants in code (0122, 01A2, 0222) ---
    print("\n--- LDX #imm near 8380FF (decompress region) ---")
    region = rom[lorom(0x83, 0x8000) : lorom(0x83, 0x8200)]
    for imm in (0x0122, 0x0142, 0x0166, 0x01A2, 0x0222):
        pat = bytes([0xA2, imm & 0xFF, (imm >> 8) & 0xFF])
        idx = 0
        while True:
            j = region.find(pat, idx)
            if j < 0:
                break
            snes = 0x838000 + j
            print(f"  LDX #{imm:04X} @ ${snes:06X}")
            idx = j + 1

    # --- F4AB text engine ---
    off = lorom(0x80, 0xF4AB)
    print("\n--- $80:F4AB (text engine) ---")
    for line in disasm_65816(rom[off : off + 96], 0x80F4AB, 30):
        print(line)

    # --- D63B prologue driver start ---
    off = lorom(0x87, 0xD63B)
    print("\n--- $87:D63B (prologue driver, first 30 ops) ---")
    for line in disasm_65816(rom[off : off + 120], 0x87D63B, 30):
        print(line)

    # --- Search for 7C00 VRAM tilemap refs ---
    print("\n--- VRAM $007C00 references (dialog tilemap) ---")
    for rom_off in scan_abs24(rom, 0x007C00)[:15]:
        print(f"  ROM ${rom_off:06X} / SNES ${rom_to_snes(rom_off):06X}")

    # --- 8380FF caller context ---
    off = lorom(0x83, 0x80E0)
    print("\n--- $83:80E0..8100 (around decompress) ---")
    for line in disasm_65816(rom[off : off + 48], 0x8380E0, 20):
        print(line)


if __name__ == "__main__":
    main()
