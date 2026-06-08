import struct

font = {}
with open('nage_libre.tbl', 'r', encoding='utf-8') as f:
    for line in f:
        if '=' in line:
            hx, ch = line.strip().split('=')
            font[int(hx, 16)] = ch

with open('Nage Libre - Seijaku no Suishin (Japan).sfc', 'rb') as f:
    rom = bytearray(f.read())

def lorom(bank, addr): return (bank & 0x7F) * 0x8000 + (addr - 0x8000)

start = lorom(0x87, 0x8000)
end = lorom(0x87, 0x8FFF)

for ptr in range(0x8000, 0x8FFF):
    off = lorom(0x87, ptr)
    # look for FFFF terminated string
    text = ""
    i = off
    valid = True
    length = 0
    while i < end:
        cid = rom[i] | (rom[i+1] << 8)
        if cid == 0xFFFF:
            break
        if cid == 0x03FE: text += " "
        elif cid == 0x00AE: text += "…"
        elif cid in font: text += font[cid]
        else: text += f"[{cid:04X}]"
        i += 2
        length += 1
        if length > 50:
            valid = False
            break
    if valid and length >= 5:
        print(f"87:{ptr:04X}: {text}")

