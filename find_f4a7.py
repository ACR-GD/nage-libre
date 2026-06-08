import struct
with open('Nage Libre - Seijaku no Suishin (Japan).sfc', 'rb') as f:
    rom = bytearray(f.read())
def lorom(bank, addr): return (bank & 0x7F) * 0x8000 + (addr - 0x8000)

bank87 = rom[lorom(0x87, 0x8000):lorom(0x87, 0xFFFF)]
target = bytes([0x22, 0xA7, 0xF4, 0x80])
idx = -1
while True:
    idx = bank87.find(target, idx+1)
    if idx == -1: break
    addr = 0x8000 + idx
    print(f"Found JSL F4A7 at 87:{addr:04X}")
