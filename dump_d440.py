import struct
with open('Nage Libre - Seijaku no Suishin (Japan).sfc', 'rb') as f:
    rom = bytearray(f.read())
def lorom(bank, addr): return (bank & 0x7F) * 0x8000 + (addr - 0x8000)

off = lorom(0x87, 0xD440)
code = rom[off:off+16]
print("87:D440:", ' '.join(f'{b:02X}' for b in code))
