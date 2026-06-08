with open('Nage Libre - Seijaku no Suishin (Japan).sfc', 'rb') as f:
    rom = bytearray(f.read())
off = 0x038181
print(' '.join(f'{b:02X}' for b in rom[off:off+16]))
