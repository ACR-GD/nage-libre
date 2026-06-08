with open('Nage Libre - Seijaku no Suishin (Japan).sfc', 'rb') as f:
    rom = bytearray(f.read())
off = 0x0FD44A
code = rom[off:off+64]
print(' '.join(f'{b:02X}' for b in code))
