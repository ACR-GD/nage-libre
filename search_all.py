import struct
with open('Nage Libre - Seijaku no Suishin (Japan).sfc', 'rb') as f:
    rom = f.read()

# この世界 = 0088 001C 0068 00FC
pattern = bytes([0x88, 0x00, 0x1C, 0x00, 0x68, 0x00, 0xFC, 0x00])

idx = 0
while True:
    idx = rom.find(pattern, idx)
    if idx == -1:
        break
    bank = idx // 0x8000
    addr = 0x8000 + (idx % 0x8000)
    print(f"Found pattern at ROM offset {idx:06X} (Bank {bank|0x80:02X}:{addr:04X})")
    idx += 1
