import struct
with open('Nage Libre - Seijaku no Suishin (Japan).sfc', 'rb') as f:
    rom = bytearray(f.read())
def lorom(bank, addr): return (bank & 0x7F) * 0x8000 + (addr - 0x8000)

bank87 = rom[lorom(0x87, 0x8000):lorom(0x87, 0x10000)]
for i in range(len(bank87)-7):
    if bank87[i:i+4] == b'\xA9\x51\x8A\x87': # Wait, LDA #$8A51
        pass
    if bank87[i:i+4] == b'\xA9\x51\x85\x09': # LDA #$51; STA $09
        print(f"Found LDA #$51 at $87:{0x8000+i:04X}")

for i in range(len(rom)-3):
    if rom[i:i+2] == b'\x51\x8A':
        pass
