import struct
with open('Nage Libre - Seijaku no Suishin (Japan).sfc', 'rb') as f:
    rom = bytearray(f.read())
def lorom(bank, addr): return (bank & 0x7F) * 0x8000 + (addr - 0x8000)

bank87 = rom[lorom(0x87, 0x8000):lorom(0x87, 0x10000)]
for i in range(len(bank87)-4):
    if bank87[i] == 0xBF and bank87[i+3] == 0x85 and bank87[i+4] == 0x09: # LDA long,X \ STA $09
        print(f"Found LDA long,X \ STA $09 at $87:{0x8000+i:04X}")
