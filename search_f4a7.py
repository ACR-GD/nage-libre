import struct
with open('Nage Libre - Seijaku no Suishin (Japan).sfc', 'rb') as f:
    rom = bytearray(f.read())
def lorom(bank, addr): return (bank & 0x7F) * 0x8000 + (addr - 0x8000)

for i in range(len(rom)-3):
    if rom[i:i+4] == b'\x22\xA7\xF4\x80':
        bank = i // 0x8000
        addr = 0x8000 + (i % 0x8000)
        print(f"Found JSL $80:F4A7 at ${bank|0x80:02X}:{addr:04X}")
