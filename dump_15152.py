with open('Nage Libre - Seijaku no Suishin (Japan).sfc', 'rb') as f:
    rom = bytearray(f.read())
off = 0x015152 - 4
code = rom[off:off+16]
print(' '.join(f'{b:02X}' for b in code))
