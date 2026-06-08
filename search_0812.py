import struct
with open('Nage Libre - Seijaku no Suishin (Japan).sfc', 'rb') as f:
    rom = bytearray(f.read())
def lorom(bank, addr): return (bank & 0x7F) * 0x8000 + (addr - 0x8000)

for i in range(len(rom)-2):
    if rom[i:i+3] == b'\x12\x08\x00' or rom[i:i+2] == b'\x12\x08':
        bank = i // 0x8000
        addr = 0x8000 + (i % 0x8000)
        # print(f"Found 0812 at ${bank|0x80:02X}:{addr:04X}")
