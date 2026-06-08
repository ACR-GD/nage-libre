import struct
with open('Nage Libre - Seijaku no Suishin (Japan).sfc', 'rb') as f:
    rom = bytearray(f.read())
def lorom(bank, addr): return (bank & 0x7F) * 0x8000 + (addr - 0x8000)

start = lorom(0x87, 0x89C5)
code = rom[start:start+64]
print("87:89C5:")
for i in range(0, len(code), 2):
    val = struct.unpack_from('<H', code, i)[0]
    print(f"{val:04X}", end=' ')
    if val == 0xFFFF:
        break
print()
