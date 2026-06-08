import struct
with open('Nage Libre - Seijaku no Suishin (Japan).sfc', 'rb') as f:
    rom = bytearray(f.read())
def lorom(bank, addr): return (bank & 0x7F) * 0x8000 + (addr - 0x8000)

start = 0x038C01
end = 0x038D00
print(f"Bytes after 0x038C01:")
for i in range(start, end, 16):
    print(' '.join(f'{b:02X}' for b in rom[i:i+16]))
