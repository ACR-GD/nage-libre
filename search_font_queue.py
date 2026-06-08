import struct
with open('Nage Libre - Seijaku no Suishin (Japan).sfc', 'rb') as f:
    rom = bytearray(f.read())
def lorom(bank, addr): return (bank & 0x7F) * 0x8000 + (addr - 0x8000)

for i in range(len(rom)-2):
    if rom[i:i+3] == b'\xBD\x4A\x07': # LDA $074A,X
        bank = i // 0x8000
        addr = 0x8000 + (i % 0x8000)
        print(f"Found LDA $074A,X at ${bank|0x80:02X}:{addr:04X}")
    if rom[i:i+3] == b'\xBD\x4C\x07': # LDA $074C,X
        bank = i // 0x8000
        addr = 0x8000 + (i % 0x8000)
        print(f"Found LDA $074C,X at ${bank|0x80:02X}:{addr:04X}")
