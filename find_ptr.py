import struct
with open('Nage Libre - Seijaku no Suishin (Japan).sfc', 'rb') as f:
    rom = bytearray(f.read())
for i in range(len(rom) - 2):
    if rom[i] == 0x6D and rom[i+1] == 0x89:
        addr = 0x800000 + (i // 0x8000) * 0x10000 + (i % 0x8000) + 0x8000
        print(f"Found 6D 89 at {hex(addr)}")
