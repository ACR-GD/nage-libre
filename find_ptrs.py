import struct
with open('Nage Libre - Seijaku no Suishin (Japan).sfc', 'rb') as f:
    rom = bytearray(f.read())

ptrs = [(0x89, 0xC5), (0x89, 0xDF), (0x89, 0x2F), (0x89, 0x49)]
for p in ptrs:
    print(f"Searching for {p[1]:02X} {p[0]:02X}")
    for i in range(len(rom)-1):
        if rom[i] == p[1] and rom[i+1] == p[0]:
            print(f"Found at 0x{i:06X}")
