import struct
with open('Nage Libre - Seijaku no Suishin (Japan).sfc', 'rb') as f:
    rom = bytearray(f.read())
def lorom(bank, addr): return (bank & 0x7F) * 0x8000 + (addr - 0x8000)

off = lorom(0x80, 0xF6E8)
print("F6E8 subroutine:")
hx = ' '.join(f'{b:02X}' for b in rom[off:off+128])
print(hx)
