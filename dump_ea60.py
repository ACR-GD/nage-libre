import struct
with open('Nage Libre - Seijaku no Suishin (Japan).sfc', 'rb') as f:
    rom = bytearray(f.read())
def lorom(bank, addr): return (bank & 0x7F) * 0x8000 + (addr - 0x8000)

hx = ' '.join(f'{b:02X}' for b in rom[lorom(0x87, 0xEA60):lorom(0x87, 0xEAC0)])
print("87:EA60:", hx)
