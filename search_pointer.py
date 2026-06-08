import struct
with open('Nage Libre - Seijaku no Suishin (Japan).sfc', 'rb') as f:
    rom = bytearray(f.read())
def lorom(bank, addr): return (bank & 0x7F) * 0x8000 + (addr - 0x8000)

for i in range(len(rom)-1):
    if rom[i:i+2] == b'\xC5\x89':
        bank = i // 0x8000
        addr = 0x8000 + (i % 0x8000)
        print(f"Found C5 89 at ${bank|0x80:02X}:{addr:04X}")
    if rom[i:i+3] == b'\xC5\x89\x87':
        bank = i // 0x8000
        addr = 0x8000 + (i % 0x8000)
        print(f"Found C5 89 87 at ${bank|0x80:02X}:{addr:04X}")
