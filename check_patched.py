import struct
with open('Nage Libre - Patched.sfc', 'rb') as f:
    rom = bytearray(f.read())
def lorom(bank, addr): return (bank & 0x7F) * 0x8000 + (addr - 0x8000)

print("87:D3C7:", ' '.join(f'{b:02X}' for b in rom[lorom(0x87, 0xD3C7):lorom(0x87, 0xD3C7)+16]))
print("87:EA36:", ' '.join(f'{b:02X}' for b in rom[lorom(0x87, 0xEA36):lorom(0x87, 0xEA36)+16]))
