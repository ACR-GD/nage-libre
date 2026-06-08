import struct
with open('Nage Libre - Seijaku no Suishin (Japan).sfc', 'rb') as f:
    rom = bytearray(f.read())
def lorom(bank, addr): return (bank & 0x7F) * 0x8000 + (addr - 0x8000)

bank87 = rom[lorom(0x87, 0x8000):lorom(0x87, 0xFFFF)]
free_start = -1
for i in range(len(bank87)-1, -1, -1):
    if bank87[i] != 0xFF and bank87[i] != 0x00:
        free_start = i + 1
        break

print(f"Free space in Bank 87 starts at 87:{0x8000 + free_start:04X} ({len(bank87) - free_start} bytes)")
