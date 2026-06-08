import struct
with open('Nage Libre - Seijaku no Suishin (Japan).sfc', 'rb') as f:
    rom = bytearray(f.read())
def lorom(bank, addr): return (bank & 0x7F) * 0x8000 + (addr - 0x8000)

def dis(bank, addr, sz):
    off = lorom(bank, addr)
    hx = ' '.join(f'{b:02X}' for b in rom[off:off+sz])
    print(f"${bank:02X}:{addr:04X}: {hx}")

print("80:8843:")
dis(0x80, 0x8843, 32)
print("80:FA63:")
dis(0x80, 0xFA63, 32)
print("80:86FA:")
dis(0x80, 0x86FA, 32)
print("82:BBC5:")
dis(0x82, 0xBBC5, 64)
