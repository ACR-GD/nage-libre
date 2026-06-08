import struct
with open('Nage Libre - Seijaku no Suishin (Japan).sfc', 'rb') as f:
    rom = bytearray(f.read())
def lorom(bank, addr): return (bank & 0x7F) * 0x8000 + (addr - 0x8000)

bank87 = rom[lorom(0x87, 0x8000):lorom(0x87, 0xFFFF)]
print("Hardcoded pointers in Bank 87:")
for i in range(len(bank87) - 12):
    # A9 xx 85 09 A9 yy 85 0A A9 zz 85 0B
    if (bank87[i] == 0xA9 and bank87[i+2] == 0x85 and bank87[i+3] == 0x09 and
        bank87[i+4] == 0xA9 and bank87[i+6] == 0x85 and bank87[i+7] == 0x0A and
        bank87[i+8] == 0xA9 and bank87[i+10] == 0x85 and bank87[i+11] == 0x0B):
        addr = 0x8000 + i
        ptr = bank87[i+1] | (bank87[i+5] << 8)
        bank = bank87[i+9]
        print(f"At 87:{addr:04X} -> Pointer {bank:02X}:{ptr:04X}")
