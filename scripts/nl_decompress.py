#!/usr/bin/env python3
"""Décompresseur statique Nage Libre (reverse de $80:F8D8), validé bit-à-bit
contre le buffer $7F:64C0 du prologue (région programme identique + source
consommée exactement jusqu'à $A5:F34D).

Format (codec custom à nibbles + fenêtre 4 octets) :
  - Flux de nibbles lus dans [$09] : octet -> nibble haut puis nibble bas.
  - 1er octet source = octet de contrôle (8 bits de poids fort des littéraux).
  - Commande = 1 nibble :
      0-7  : octet littéral = ((cmd<<4)|nibble) | (bit MSB du flux de contrôle).
             Le contrôle est décalé à chaque littéral ; rechargé (1 octet = 2
             nibbles) tous les 8 littéraux.
      8    : RLE de mot 16 bits = répète les 2 derniers octets « count » fois
             (count = octet ; étendu tant que l'octet vaut 0xFF).
      9    : fin du flux.
      10/11: octet 0x00 / 0xFF.
      12-15: recopie window[cmd-12] (4 derniers octets, positions absolues).
  Octets littéraux / 0x00 / 0xFF / window poussés dans la fenêtre ; le RLE non.

La table de pointeurs source 24 bits est à $8A:8000 (entrées de 3 octets,
indexées par scène). Le code de scène ($83:80DB) décompresse vers $7F:64C0.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ROM = ROOT / "Nage Libre - Seijaku no Suishin (Japan).sfc"

PTR_TABLE = 0x8A8000   # $8A:8000 (SNES) — table de pointeurs source
DEST_SCRIPT = 0x7F64C0  # destination des scènes de texte


def lorom_off(snes24):
    bank = (snes24 >> 16) & 0xFF
    addr = snes24 & 0xFFFF
    return ((bank & 0x7F) * 0x8000) + (addr - 0x8000)


def decompress(rom, src_off, dst_limit=0x8000, max_steps=2_000_000):
    """Décompresse à partir de l'offset fichier src_off. Renvoie (octets, fin_src)."""
    pos = src_off
    nibc = 0
    nibb = 0

    def nbyte():
        nonlocal pos
        b = rom[pos]
        pos += 1
        return b

    def nnib():
        nonlocal nibc, nibb
        nibc += 1
        if nibc & 1:
            nibb = nbyte()
            return nibb >> 4
        return nibb & 0x0F

    out = bytearray()
    window = [0xFF, 0xFF, 0xFF, 0xFF]
    ring = 0

    def push(b):
        nonlocal ring
        out.append(b)
        window[ring] = b
        ring = (ring + 1) & 3

    control = nbyte()
    litc = 0
    steps = 0
    while steps < max_steps:
        steps += 1
        cmd = nnib()
        if cmd <= 7:
            val = (cmd << 4) | nnib()
            msb = control & 0x80
            control = (control << 1) & 0xFF
            push(val | msb)
            litc += 1
            if litc == 8:
                control = (nnib() << 4) | nnib()
                litc = 0
        elif cmd == 8:
            cnt = 0
            while True:
                bc = (nnib() << 4) | nnib()
                cnt += bc
                if bc != 0xFF:
                    break
            b1 = window[(ring + 2) & 3]
            b2 = window[(ring + 3) & 3]
            for _ in range(cnt):
                out.append(b1)
                out.append(b2)
        elif cmd == 9:
            break
        elif cmd == 10:
            push(0x00)
        elif cmd == 11:
            push(0xFF)
        else:
            push(window[cmd - 12])
        if len(out) >= dst_limit:
            break
    return bytes(out), pos


def read_ptr_table(rom, count):
    """count entrées de 3 octets à $8A:8000 -> liste de (idx, snes24, file_off|None)."""
    base = lorom_off(PTR_TABLE)
    out = []
    for i in range(count):
        a = base + i * 3
        addr = rom[a] | (rom[a + 1] << 8)
        bank = rom[a + 2]
        snes = (bank << 16) | addr
        valid = bank >= 0x80 and addr >= 0x8000
        out.append((i, snes, lorom_off(snes) if valid else None))
    return out


if __name__ == "__main__":
    import sys
    rom = ROM.read_bytes()
    idx = int(sys.argv[1], 0) if len(sys.argv) > 1 else 0x341
    tbl = read_ptr_table(rom, idx + 1)
    _, snes, off = tbl[idx]
    out, end = decompress(rom, off)
    print(f"idx {idx:#05x}  src ${snes:06X}  -> {len(out)} o, fin ${end//0x8000+0x80:02X}:{end%0x8000+0x8000:04X}")
