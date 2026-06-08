import struct
with open('Nage Libre - Seijaku no Suishin (Japan).sfc', 'rb') as f:
    rom = bytearray(f.read())
def lorom(bank, addr): return (bank & 0x7F) * 0x8000 + (addr - 0x8000)

bank80 = rom[0:0x8000]
free = bank80.find(b'\xFF' * 16)
if free != -1:
    print(f"Found FF free space at 80:{free+0x8000:04X}")
else:
    free = bank80.find(b'\x00' * 16)
    if free != -1:
        print(f"Found 00 free space at 80:{free+0x8000:04X}")
    else:
        print("No free space in Bank 80")
