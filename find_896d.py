import struct
with open('Nage Libre - Seijaku no Suishin (Japan).sfc', 'rb') as f:
    rom = bytearray(f.read())
def lorom(bank, addr): return (bank & 0x7F) * 0x8000 + (addr - 0x8000)

for i in range(len(rom) - 3):
    if rom[i] == 0xA9 and rom[i+1] == 0x6D and rom[i+2] == 0x89:
        addr = 0x800000 + (i // 0x8000) * 0x10000 + (i % 0x8000) + 0x8000
        print(f"Found A9 6D 89 at {hex(addr)}")
