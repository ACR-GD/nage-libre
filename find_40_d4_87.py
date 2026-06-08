import struct
with open('Nage Libre - Seijaku no Suishin (Japan).sfc', 'rb') as f:
    rom = bytearray(f.read())
count = 0
for i in range(len(rom)-2):
    if rom[i] == 0x40 and rom[i+1] == 0xD4 and rom[i+2] == 0x87:
        print(f"Found 40 D4 87 at 0x{i:06X}")
        count += 1
print(f"Total: {count}")
