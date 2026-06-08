import struct
with open('Nage Libre - Seijaku no Suishin (Japan).sfc', 'rb') as f:
    rom = bytearray(f.read())
count = 0
for i in range(len(rom)-1):
    if rom[i] == 0x40 and rom[i+1] == 0xD4:
        print(f"Found 40 D4 at 0x{i:06X}")
        count += 1
print(f"Total: {count}")
