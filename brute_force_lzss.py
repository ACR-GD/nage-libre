import sys

def decompress(rom, start_addr, max_len=8):
    ptr = start_addr
    nibble_state = 0
    curr_byte = 0
    def get_nibble():
        nonlocal nibble_state, curr_byte, ptr
        nibble_state += 1
        if nibble_state & 1:
            if ptr >= len(rom):
                return -1
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

if __name__ == '__main__':
    with open('/Users/acr/Develop/nage-libre/Nage Libre - Seijaku no Suishin (Japan).sfc', 'rb') as f:
        rom = f.read()
    
    target = bytearray([0x5A, 0x07, 0x2A, 0x00, 0x68, 0x00])
    
    for i in range(len(rom) - 100):
        if i % 100000 == 0:
            print(f"Scanning {i:06X}...")
        try:
            out = decompress(rom, i, max_len=6)
            if out[:6] == target:
                print(f"FOUND TARGET AT 0x{i:06X}")
                full_out = decompress(rom, i, max_len=100)
                print("Full Decompressed Output:")
                print(' '.join(f'{b:02X}' for b in full_out[:32]))
                break
        except Exception as e:
            pass
