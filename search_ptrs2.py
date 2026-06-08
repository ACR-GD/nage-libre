import struct
with open('Nage Libre - Seijaku no Suishin (Japan).sfc', 'rb') as f:
    rom = bytearray(f.read())
def lorom(bank, addr): return (bank & 0x7F) * 0x8000 + (addr - 0x8000)

for bank in range(0x80, 0xC0):
    bank_data = rom[lorom(bank, 0x8000):lorom(bank, 0x10000)]
    for i in range(len(bank_data)-1):
        if bank_data[i:i+2] == b'\xC5\x89':
            print(f"Found C5 89 at ${bank:02X}:{0x8000+i:04X}")
