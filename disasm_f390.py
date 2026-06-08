import struct
with open('Nage Libre - Seijaku no Suishin (Japan).sfc', 'rb') as f:
    rom = bytearray(f.read())
def lorom(bank, addr): return (bank & 0x7F) * 0x8000 + (addr - 0x8000)

def dis(bank, addr, sz):
    off = lorom(bank, addr)
    hx = ' '.join(f'{b:02X}' for b in rom[off:off+sz])
    print(f"${bank:02X}:{addr:04X}: {hx}")

dis(0x80, 0xF390, 64)
