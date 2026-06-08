import sys

def decompress(rom, start_addr, max_len=65536):
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
    
    try:
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
                break
    except Exception:
        pass
            
    return out

with open('/Users/acr/Develop/nage-libre/Nage Libre - Seijaku no Suishin (Japan).sfc', 'rb') as f:
    rom = f.read()

target = bytes([0x5A, 0x07, 0x2A, 0x00, 0x68, 0x00])

blocks = [
    0x1484FC, 0x040000, 0x048000, 0x110000, 0x12376B, 0x102284, 0x154977,
    0x168000, 0x158000, 0x0E8000, 0x05247E, 0x15C30E, 0x0ECFE6, 0x0667FD,
    0x06154A, 0x16D842, 0x16C017, 0x05EA9A, 0x0B8976, 0x150000
]

for b in blocks:
    out = decompress(rom, b)
    if target in out:
        print(f"FOUND IN BLOCK 0x{b:06X}!")
    else:
        print(f"Block 0x{b:06X} decompressed to {len(out)} bytes. Not found.")
