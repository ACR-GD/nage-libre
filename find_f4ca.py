import struct
with open('Nage Libre - Seijaku no Suishin (Japan).sfc', 'rb') as f:
    rom = bytearray(f.read())
count = 0
for i in range(len(rom)-3):
    if rom[i] == 0x22 and rom[i+1] == 0xCA and rom[i+2] == 0xF4 and rom[i+3] == 0x80:
        print(f"Found JSL 80:F4CA at 0x{i:06X}")
        count += 1
print(f"Total JSL F4CA: {count}")

for i in range(len(rom)-2):
    if rom[i] == 0x20 and rom[i+1] == 0xCA and rom[i+2] == 0xF4:
        print(f"Found JSR F4CA at 0x{i:06X}")
