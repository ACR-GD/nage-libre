import struct
with open('Nage Libre - Seijaku no Suishin (Japan).sfc', 'rb') as f:
    rom = bytearray(f.read())
def lorom(bank, addr): return (bank & 0x7F) * 0x8000 + (addr - 0x8000)

start = lorom(0x87, 0xEA45)
code = rom[start:start+128]
print("87:EA45:")
for i in range(0, len(code), 4):
    print(' '.join(f'{b:02X}' for b in code[i:i+4]))
