import struct
with open('Nage Libre - Seijaku no Suishin (Japan).sfc', 'rb') as f:
    rom = bytearray(f.read())
def lorom(bank, addr): return (bank & 0x7F) * 0x8000 + (addr - 0x8000)

def dis(addr, sz):
    hx = ' '.join(f'{b:02X}' for b in rom[lorom(0x87, addr):lorom(0x87, addr)+sz])
    print(f"87:{addr:04X}: {hx}")

dis(0xEB2C, 64)
