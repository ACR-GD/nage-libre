with open('Nage Libre - Seijaku no Suishin (Japan).sfc', 'rb') as f:
    rom = bytearray(f.read())
seq = bytes([0xA9, 0xC5, 0x85, 0x09, 0xA9, 0x89, 0x85, 0x0A])
count = 0
for i in range(len(rom) - len(seq)):
    if rom[i:i+len(seq)] == seq:
        print(f"Found at 0x{i:06X}")
        count += 1
print(f"Total: {count}")
