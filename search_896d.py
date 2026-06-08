import struct
with open('Nage Libre - Seijaku no Suishin (Japan).sfc', 'rb') as f:
    rom = bytearray(f.read())
def lorom(bank, addr): return (bank & 0x7F) * 0x8000 + (addr - 0x8000)

bank87 = rom[lorom(0x87, 0x8000):lorom(0x87, 0x10000)]
for i in range(len(bank87)-7):
    if bank87[i:i+4] == b'\xA9\x6D\x85\x09': 
        print(f"Found LDA #$6D at $87:{0x8000+i:04X}")
        hx = ' '.join(f'{b:02X}' for b in bank87[i:i+16])
        print(f"  {hx}")
