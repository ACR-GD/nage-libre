import sys

def decompress(rom, start_addr):
    ptr = start_addr
    nibble_state = 0
    curr_byte = 0
    def get_nibble():
        nonlocal nibble_state, curr_byte, ptr
        nibble_state += 1
        if nibble_state & 1:
            curr_byte = rom[ptr]
            ptr += 1
            return curr_byte >> 4
        else:
            return curr_byte & 0x0F
            
    def get_byte():
        hi = get_nibble()
        lo = get_nibble()
        return (hi << 4) | lo

    out = bytearray()
    history = bytearray([0xFF, 0xFF, 0xFF, 0xFF])
    dd = 0
    
    # 02DB flag byte
    flag_byte = get_byte()
    flag_bits = 8
    
    while len(out) < 200:
        cmd = get_nibble()
        if cmd <= 6:
            # Literal
            # F92B
            val = (cmd << 3)
            val = val | get_nibble()
            
            # flag bit
            if flag_bits == 0:
                flag_byte = get_byte()
                flag_bits = 8
            bit = (flag_byte >> 7) & 1
            flag_byte = (flag_byte << 1) & 0xFF
            flag_bits -= 1
            
            val = val | (bit << 7)
            
            out.append(val)
            history[dd] = val
            dd = (dd + 1) & 3
        elif cmd == 7:
            # F97C (RLE)
            length = 0
            while True:
                b = get_byte()
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
            print(f"UNIMPLEMENTED CMD: {cmd:X}")
            break
            
    return out

if __name__ == '__main__':
    with open('/Users/acr/Develop/nage-libre/Nage Libre - Seijaku no Suishin (Japan).sfc', 'rb') as f:
        rom = f.read()
    
    out = decompress(rom, 0x128000)
    print("Decompressed bytes:")
    print(' '.join(f'{b:02X}' for b in out[:32]))
