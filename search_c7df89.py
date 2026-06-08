with open('Nage Libre - Seijaku no Suishin (Japan).sfc', 'rb') as f:
    rom = bytearray(f.read())
seq = bytes([0xC7, 0xDF, 0x89])
for i in range(len(rom)-2):
    if rom[i:i+3] == seq:
        print(f"Found C7 DF 89 at 0x{i:06X}")
