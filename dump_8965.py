import struct
with open('Nage Libre - Seijaku no Suishin (Japan).sfc', 'rb') as f:
    rom = bytearray(f.read())
def lorom(bank, addr): return (bank & 0x7F) * 0x8000 + (addr - 0x8000)

off = lorom(0x87, 0x8965)
hx = ' '.join(f'{b:02X}' for b in rom[off:off+32])
print("87:8965:", hx)
