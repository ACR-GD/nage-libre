import struct
with open('Nage Libre - Seijaku no Suishin (Japan).sfc', 'rb') as f:
    rom = bytearray(f.read())
def lorom(bank, addr): return (bank & 0x7F) * 0x8000 + (addr - 0x8000)

start = lorom(0x87, 0xD440)
code = rom[start:start+32]
print("87:D440:")
for i in range(0, len(code), 2):
    ptr = struct.unpack_from('<H', code, i)[0]
    print(f"Ptr: {ptr:04X}")
