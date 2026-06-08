import struct
with open('Nage Libre - Seijaku no Suishin (Japan).sfc', 'rb') as f:
    rom = bytearray(f.read())
def lorom(bank, addr): return (bank & 0x7F) * 0x8000 + (addr - 0x8000)

bank87 = rom[lorom(0x87, 0x8000):lorom(0x87, 0x10000)]
for i in range(len(bank87)-2):
    if bank87[i:i+3] == b'\xAD\xD4\x17':
        print(f"Found LDA $17D4 at $87:{0x8000+i:04X}")
