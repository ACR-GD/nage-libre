with open('Nage Libre - Seijaku no Suishin (Japan).sfc', 'rb') as f:
    rom = f.read()

def lorom(bank, addr):
    return (bank & 0x7F) * 0x8000 + (addr - 0x8000)

off = lorom(0x80, 0xF433)
data = rom[off:off+64]
hx = ' '.join(f'{b:02X}' for b in data)
print("F433:", hx)
