import struct
from build_patched_rom import ROM_PATH, FONT
with open(ROM_PATH, 'rb') as f: rom = bytearray(f.read())
def lorom(bank, addr): return (bank & 0x7F) * 0x8000 + (addr - 0x8000)

ptrs = [0x88DB, 0x88F7, 0x8913, 0x892F, 0x8949, 0x8965, 0x8969, 0x896D, 0x899B, 0x89B7, 0x89C1, 0x89C5, 0x89DF, 0x89EB, 0x8A51, 0x8A61, 0x8A71]

for ptr in ptrs:
    start = lorom(0x87, ptr)
    text = ""
    for i in range(start, start+100, 2):
        cid = rom[i] | (rom[i+1] << 8)
        if cid == 0xFFFF: break
        if cid == 0x03FE: text += " "
        elif cid in FONT: text += FONT[cid]
        else: text += f"[{cid:04X}]"
    print(f"87:{ptr:04X}: {text}")
