import struct
from build_patched_rom import ROM_PATH

def parse_text_table(rom):
    TABLE_START, TABLE_END = 0x038697, 0x038C01
    orig = []
    i, line = TABLE_START, 0
    cur, start_off = [], TABLE_START
    while i < TABLE_END:
        w = rom[i] | (rom[i+1] << 8)
        if w == 0xFFFF:
            orig.append({'line': line, 'rom': start_off, 'ids': cur[:]})
            line += 1; cur = []; i += 2; start_off = i
        else:
            cur.append(w); i += 2
    if cur: orig.append({'line': line, 'rom': start_off, 'ids': cur[:]})
    return orig

with open(ROM_PATH, 'rb') as f: rom = bytearray(f.read())
strings = parse_text_table(rom)

for s in strings:
    if len(s['ids']) > 10:
        print(f"Line {s['line']}: len {len(s['ids'])} : {[hex(x) for x in s['ids'][:5]]}")
