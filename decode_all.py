import struct
from build_patched_rom import ROM_PATH, FONT
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
    text = ""
    for cid in s['ids']:
        if cid == 0x03FE: text += " "
        elif cid in FONT: text += FONT[cid]
        else: text += f"[{cid:04X}]"
    print(f"Line {s['line']}: {text}")
