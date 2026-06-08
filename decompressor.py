import sys

def decompress(rom, start_addr, max_out_bytes=1000):
    memory = bytearray(0x10000)
    
    a = 0
    x = 0
    y = 0
    
    flag_m = 1  
    flag_x = 1  
    flag_c = 0
    flag_z = 0
    flag_n = 0
    
    rom_ptr = start_addr
    
    memory[0x02D9] = 0
    memory[0x02DC] = 0
    memory[0x02DD] = 0
    memory[0x02DE] = 0
    memory[0x02DF] = 0xFF
    memory[0x02E0] = 0xFF
    memory[0x02E1] = 0xFF
    memory[0x02E2] = 0xFF
    
    output = bytearray()
    
    def update_zn(val, bits):
        nonlocal flag_z, flag_n
        flag_z = 1 if val == 0 else 0
        if bits == 8:
            flag_n = 1 if (val & 0x80) else 0
        else:
            flag_n = 1 if (val & 0x8000) else 0

    code = rom[0:0x8000] 
    
    op_count = 0
    
    while len(output) < max_out_bytes and op_count < 200000:
        pc = 0x07929  # Start of decompression subroutine
        call_stack = []
        
        while True:
            op_count += 1
            if op_count > 200000: break
            
            if pc == 0x07A4C:
                val = rom[rom_ptr]
                if flag_m:
                    a = (a & 0xFF00) | val
                    update_zn(val, 8)
                else:
                    a = rom[rom_ptr] | (rom[rom_ptr+1] << 8)
                    update_zn(a, 16)
                pc += 2
                continue
                
            if pc == 0x07A50:
                rom_ptr += 1
                pc += 2
                continue
                
            op = code[pc]
            
            if op == 0x87 and code[pc+1] == 0x06:
                val = a & 0xFF if flag_m else a & 0xFFFF
                output.append(val & 0xFF)
                if not flag_m:
                    output.append((val >> 8) & 0xFF)
                pc += 2
                continue
                
            if op == 0xE6 and code[pc+1] == 0x06:
                pc += 2
                continue
                
            if op == 0x20: 
                addr = code[pc+1] | (code[pc+2] << 8)
                call_stack.append(pc + 3)
                pc = addr & 0x7FFF 
                continue
            elif op == 0x60: 
                if not call_stack:
                    break
                pc = call_stack.pop()
                continue
            elif op == 0x8D: 
                addr = code[pc+1] | (code[pc+2] << 8)
                if flag_m:
                    memory[addr] = a & 0xFF
                    if op_count < 200: print(f"  STA abs {addr:04X} <- {a & 0xFF:02X}")
                else:
                    memory[addr] = a & 0xFF
                    memory[addr+1] = (a >> 8) & 0xFF
                pc += 3
            elif op == 0xAD: 
                addr = code[pc+1] | (code[pc+2] << 8)
                if flag_m:
                    val = memory[addr]
                    a = (a & 0xFF00) | val
                    update_zn(val, 8)
                else:
                    val = memory[addr] | (memory[addr+1] << 8)
                    a = val
                    update_zn(val, 16)
                pc += 3
            elif op == 0x0E: 
                addr = code[pc+1] | (code[pc+2] << 8)
                if flag_m:
                    val = memory[addr]
                    flag_c = (val & 0x80) >> 7
                    val = (val << 1) & 0xFF
                    memory[addr] = val
                    update_zn(val, 8)
                else:
                    val = memory[addr] | (memory[addr+1] << 8)
                    flag_c = (val & 0x8000) >> 15
                    val = (val << 1) & 0xFFFF
                    memory[addr] = val & 0xFF
                    memory[addr+1] = (val >> 8) & 0xFF
                    update_zn(val, 16)
                pc += 3
            elif op == 0x29: 
                if flag_m:
                    val = code[pc+1]
                    res = (a & 0xFF) & val
                    a = (a & 0xFF00) | res
                    update_zn(res, 8)
                    pc += 2
                else:
                    val = code[pc+1] | (code[pc+2] << 8)
                    a = a & val
                    update_zn(a, 16)
                    pc += 3
            elif op == 0x0D: 
                addr = code[pc+1] | (code[pc+2] << 8)
                if flag_m:
                    val = memory[addr]
                    res = (a & 0xFF) | val
                    a = (a & 0xFF00) | res
                    update_zn(res, 8)
                else:
                    val = memory[addr] | (memory[addr+1] << 8)
                    a = a | val
                    update_zn(a, 16)
                pc += 3
            elif op == 0xEE: 
                addr = code[pc+1] | (code[pc+2] << 8)
                if flag_m:
                    val = (memory[addr] + 1) & 0xFF
                    memory[addr] = val
                    update_zn(val, 8)
                else:
                    val = (memory[addr] | (memory[addr+1] << 8)) + 1
                    memory[addr] = val & 0xFF
                    memory[addr+1] = (val >> 8) & 0xFF
                    update_zn(val, 16)
                pc += 3
            elif op == 0xC2: 
                val = code[pc+1]
                if val & 0x20: flag_m = 0
                if val & 0x10: flag_x = 0
                pc += 2
            elif op == 0xE2: 
                val = code[pc+1]
                if val & 0x20: flag_m = 1
                if val & 0x10: flag_x = 1
                pc += 2
            elif op == 0xAE: 
                addr = code[pc+1] | (code[pc+2] << 8)
                if flag_x:
                    x = memory[addr]
                    update_zn(x, 8)
                else:
                    x = memory[addr] | (memory[addr+1] << 8)
                    update_zn(x, 16)
                pc += 3
            elif op == 0x9D: 
                addr = (code[pc+1] | (code[pc+2] << 8)) + x
                if flag_m:
                    memory[addr & 0xFFFF] = a & 0xFF
                else:
                    memory[addr & 0xFFFF] = a & 0xFF
                    memory[(addr+1) & 0xFFFF] = (a >> 8) & 0xFF
                pc += 3
            elif op == 0x8A: 
                if flag_m:
                    a = (a & 0xFF00) | (x & 0xFF)
                    update_zn(a & 0xFF, 8)
                else:
                    a = x
                    update_zn(a, 16)
                pc += 1
            elif op == 0x1A: 
                if flag_m:
                    a = (a & 0xFF00) | ((a + 1) & 0xFF)
                    update_zn(a & 0xFF, 8)
                else:
                    a = (a + 1) & 0xFFFF
                    update_zn(a, 16)
                pc += 1
            elif op == 0xC9: 
                if flag_m:
                    val = code[pc+1]
                    res = (a & 0xFF) - val
                    update_zn(res & 0xFF, 8)
                    flag_c = 1 if (a & 0xFF) >= val else 0
                    pc += 2
                else:
                    val = code[pc+1] | (code[pc+2] << 8)
                    res = a - val
                    update_zn(res & 0xFFFF, 16)
                    flag_c = 1 if a >= val else 0
                    pc += 3
            elif op == 0xD0: 
                rel = code[pc+1]
                if rel > 127: rel -= 256
                if not flag_z:
                    pc = pc + 2 + rel
                else:
                    pc += 2
            elif op == 0x18: 
                flag_c = 0
                pc += 1
            elif op == 0x9C: 
                addr = code[pc+1] | (code[pc+2] << 8)
                if flag_m:
                    memory[addr] = 0
                else:
                    memory[addr] = 0
                    memory[addr+1] = 0
                pc += 3
            elif op == 0xAA: 
                if flag_x:
                    x = a & 0xFF
                    update_zn(x, 8)
                else:
                    x = a
                    update_zn(x, 16)
                pc += 1
            elif op == 0x6D: 
                addr = code[pc+1] | (code[pc+2] << 8)
                if flag_m:
                    val = memory[addr]
                    res = (a & 0xFF) + val + flag_c
                    flag_c = 1 if res > 0xFF else 0
                    a = (a & 0xFF00) | (res & 0xFF)
                    update_zn(a & 0xFF, 8)
                else:
                    val = memory[addr] | (memory[addr+1] << 8)
                    res = a + val + flag_c
                    flag_c = 1 if res > 0xFFFF else 0
                    a = res & 0xFFFF
                    update_zn(a, 16)
                pc += 3
            elif op == 0xF0: 
                rel = code[pc+1]
                if rel > 127: rel -= 256
                if flag_z:
                    pc = pc + 2 + rel
                else:
                    pc += 2
            elif op == 0x69: 
                if flag_m:
                    val = code[pc+1]
                    res = (a & 0xFF) + val + flag_c
                    flag_c = 1 if res > 0xFF else 0
                    a = (a & 0xFF00) | (res & 0xFF)
                    update_zn(a & 0xFF, 8)
                    pc += 2
                else:
                    val = code[pc+1] | (code[pc+2] << 8)
                    res = a + val + flag_c
                    flag_c = 1 if res > 0xFFFF else 0
                    a = res & 0xFFFF
                    update_zn(a, 16)
                    pc += 3
            elif op == 0xBD: 
                addr = (code[pc+1] | (code[pc+2] << 8)) + x
                if flag_m:
                    val = memory[addr & 0xFFFF]
                    a = (a & 0xFF00) | val
                    update_zn(val, 8)
                else:
                    val = memory[addr & 0xFFFF] | (memory[(addr+1) & 0xFFFF] << 8)
                    a = val
                    update_zn(val, 16)
                pc += 3
            elif op == 0x0A: 
                if flag_m:
                    flag_c = (a & 0x80) >> 7
                    a = (a & 0xFF00) | ((a << 1) & 0xFF)
                    update_zn(a & 0xFF, 8)
                else:
                    flag_c = (a & 0x8000) >> 15
                    a = (a << 1) & 0xFFFF
                    update_zn(a, 16)
                pc += 1
            elif op == 0x30: 
                rel = code[pc+1]
                if rel > 127: rel -= 256
                if flag_n:
                    pc = pc + 2 + rel
                else:
                    pc += 2
            elif op == 0x4A: 
                if flag_m:
                    flag_c = a & 1
                    a = (a & 0xFF00) | ((a & 0xFF) >> 1)
                    update_zn(a & 0xFF, 8)
                else:
                    flag_c = a & 1
                    a = a >> 1
                    update_zn(a, 16)
                pc += 1
            elif op == 0x80: 
                rel = code[pc+1]
                if rel > 127: rel -= 256
                pc = pc + 2 + rel
            elif op == 0xCA: 
                if flag_x:
                    x = (x - 1) & 0xFF
                    update_zn(x, 8)
                else:
                    x = (x - 1) & 0xFFFF
                    update_zn(x, 16)
                pc += 1
            elif op == 0x38: 
                flag_c = 1
                pc += 1
            elif op == 0xA9: 
                if flag_m:
                    a = (a & 0xFF00) | code[pc+1]
                    update_zn(code[pc+1], 8)
                    pc += 2
                else:
                    a = code[pc+1] | (code[pc+2] << 8)
                    update_zn(a, 16)
                    pc += 3
            elif op == 0x7C: 
                addr = (code[pc+1] | (code[pc+2] << 8)) + x
                pc = memory[addr & 0xFFFF] | (memory[(addr+1) & 0xFFFF] << 8)
                pc &= 0x7FFF
            else:
                print(f"UNIMPLEMENTED OPCODE {op:02X} at {pc:04X}")
                return bytes(output)
            
    return bytes(output)

if __name__ == '__main__':
    with open('/Users/acr/Develop/nage-libre/Nage Libre - Seijaku no Suishin (Japan).sfc', 'rb') as f:
        rom = f.read()
    
    out = decompress(rom, 0x12EE84, max_out_bytes=64)
    print("Decompressed bytes:")
    print(' '.join(f'{b:02X}' for b in out))
