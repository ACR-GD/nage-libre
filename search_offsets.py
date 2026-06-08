import struct
with open('Nage Libre - Seijaku no Suishin (Japan).sfc', 'rb') as f:
    rom = bytearray(f.read())
def lorom(bank, addr): return (bank & 0x7F) * 0x8000 + (addr - 0x8000)

for i in range(len(rom)-6):
    if rom[i:i+6] == b'\x00\x00\x04\x00\x08\x00':
        bank = i // 0x8000
        addr = 0x8000 + (i % 0x8000)
        print(f"Found table at ${bank|0x80:02X}:{addr:04X}")
