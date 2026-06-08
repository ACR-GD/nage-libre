with open('Nage Libre - Patched.sfc', 'rb') as f:
    rom = bytearray(f.read())
def lorom(bank, addr): return (bank & 0x7F) * 0x8000 + (addr - 0x8000)
off = lorom(0x87, 0xFA0C)
print("87:FA0C:", ' '.join(f'{b:02X}' for b in rom[off:off+32]))
