with open('Nage Libre - Seijaku no Suishin (Japan).sfc', 'rb') as f:
    rom = bytearray(f.read())
seq = bytes([0x6D, 0x89])
for i in range(len(rom)-1):
    if rom[i:i+2] == seq:
        print(f"Found 6D 89 at 0x{i:06X}")
