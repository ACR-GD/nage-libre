import struct
with open('Nage Libre - Seijaku no Suishin (Japan).sfc', 'rb') as f:
    rom = bytearray(f.read())
for i in range(len(rom)-1):
    if rom[i] == 0xC5 and rom[i+1] == 0x89:
        print(f"Found C5 89 at offset 0x{i:06X}")
