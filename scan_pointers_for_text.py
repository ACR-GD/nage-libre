import sys
import struct

def decompress(rom, start_addr, max_len=200):
    ptr = start_addr
    nibble_state = 0
    curr_byte = 0
    def get_nibble():
        nonlocal nibble_state, curr_byte, ptr
        nibble_state += 1
        if nibble_state & 1:
            if ptr >= len(rom): return -1
            curr_byte = rom[ptr]
            ptr += 1
            return curr_byte >> 4
        else:
            return curr_byte & 0x0F
            
    def get_byte():
        hi = get_nibble()
        if hi == -1: return -1
        lo = get_nibble()
        if lo == -1: return -1
        return (hi << 4) | lo

    out = bytearray()
    history = bytearray([0xFF, 0xFF, 0xFF, 0xFF])
    dd = 0
    
    flag_byte = get_byte()
    if flag_byte == -1: return out
    flag_bits = 8
    
    while len(out) < max_len:
        cmd = get_nibble()
        if cmd == -1: return out
        
        if cmd <= 6:
            val = (cmd << 3)
            nxt = get_nibble()
            if nxt == -1: return out
            val = val | nxt
            
            if flag_bits == 0:
                flag_byte = get_byte()
                if flag_byte == -1: return out
                flag_bits = 8
            bit = (flag_byte >> 7) & 1
            flag_byte = (flag_byte << 1) & 0xFF
            flag_bits -= 1
            
            val = val | (bit << 7)
            
            out.append(val)
            history[dd] = val
            dd = (dd + 1) & 3
        elif cmd == 7:
            length = 0
            while True:
                b = get_byte()
                if b == -1: return out
                length += b
                if b != 0xFF:
                    break
            
            e3_idx = (dd + 2) & 3
            e3 = history[e3_idx]
            
            e5_idx = (e3_idx + 1) & 3
            e5 = history[e5_idx]
            
            for _ in range(length):
                out.append(e3)
                out.append(e5)
                if len(out) >= max_len: break
        elif cmd == 8:
            break
        elif cmd == 9:
            out.append(0x00)
            history[dd] = 0x00
            dd = (dd + 1) & 3
        elif cmd == 0xA:
            out.append(0xFF)
            history[dd] = 0xFF
            dd = (dd + 1) & 3
        elif cmd in [0xB, 0xC, 0xD, 0xE]:
            val = history[cmd - 0xB]
            out.append(val)
            history[dd] = val
            dd = (dd + 1) & 3
        else:
            return out
            
    return out

with open('/Users/acr/Develop/nage-libre/Nage Libre - Seijaku no Suishin (Japan).sfc', 'rb') as f:
    rom = f.read()

pointer_tables = [
    (0x0216DB, 60),
    (0x0218E4, 60),
    (0x00AF5B, 244),
    (0x0502C4, 70),
    (0x0504F5, 96),
    (0x050678, 76),
    (0x05075C, 72),
    (0x050924, 56),
    (0x0509CC, 77),
    (0x050AB3, 97),
    (0x050BD6, 104),
    (0x050E4C, 73)
]

def check_sjis(data):
    sjis_chars = 0
    i = 0
    while i < len(data) - 1:
        if (0x81 <= data[i] <= 0x9F) or (0xE0 <= data[i] <= 0xEF):
            if (0x40 <= data[i+1] <= 0x7E) or (0x80 <= data[i+1] <= 0xFC):
                sjis_chars += 1
                i += 2
                continue
        i += 1
    return sjis_chars

for table_addr, count in pointer_tables:
    for i in range(count):
        idx = table_addr + i*3
        p_lo = rom[idx]
        p_hi = rom[idx+1]
        b = rom[idx+2]
        rom_offset = (b & 0x7F) * 0x8000 + (p_hi << 8 | p_lo) - 0x8000
        
        try:
            out = decompress(rom, rom_offset, 200)
            sjis_count = check_sjis(out)
            if sjis_count > 5:
                print(f"Table {table_addr:06X}, ptr {i}, offset {rom_offset:06X}: {sjis_count} SJIS chars!")
        except Exception:
            pass
