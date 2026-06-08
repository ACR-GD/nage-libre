import sys
import struct
import shutil
from build_patched_rom import (
    ROM_PATH, JP_SPACE,
    ScatterAllocator, encode_en, find_safe_ids,
    PROLOGUE_LINES, make_pair_tile, char_id_to_rom,
    BANK87_TRANSLATIONS
)

def lorom(bank, addr):
    return (bank & 0x7F) * 0x8000 + (addr - 0x8000)

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

def encode_to_slots(text, pad_len, alloc):
    ids = encode_en(text, alloc)
    while len(ids) < pad_len:
        ids.append(JP_SPACE)
    return ids

def install_hook1(rom, s1_l1, s1_l2):
    # Hook 1: Stamps Screen 1 (pre-rendered background) with English text
    code = bytearray()
    
    # Prologue Hook at $83:F8E3
    code += bytes([0x22, 0xD8, 0xF8, 0x80]) # JSL $80:F8D8 (Execute original LZSS decompress)
    
    # Save state and set DBR to 83
    code += bytes([0x08, 0x8B, 0xC2, 0x30, 0x48, 0xDA, 0x5A]) # PHP, PHB, REP #$30, PHA, PHX, PHY
    code += bytes([0xE2, 0x20, 0xA9, 0x83, 0x48, 0xAB, 0xC2, 0x20]) # SEP #$20, LDA #$83, PHA, PLB, REP #$20
    
    # Call subroutines to write lines
    code += bytes([0xA2, 0x22, 0x01, 0x20, 0x00, 0x00]) # LDX #$0122, JSR write_l1
    jsr_l1_addr = len(code) - 2
    code += bytes([0xA2, 0x66, 0x01, 0x20, 0x00, 0x00]) # LDX #$0166, JSR write_l2
    jsr_l2_addr = len(code) - 2
    
    # Restore state and return
    code += bytes([0x7A, 0xFA, 0x68, 0xAB, 0x28, 0x6B]) # PLY, PLX, PLA, PLB, PLP, RTL
    
    # Subroutine write_l1
    code_off = len(code)
    snes_addr = 0xF8E3 + code_off
    code[jsr_l1_addr] = snes_addr & 0xFF
    code[jsr_l1_addr+1] = (snes_addr >> 8) & 0xFF
    code += bytes([0xA0, 0x00, 0x00]) # LDY #$0000
    loop_l1 = len(code)
    code += bytes([0xB9]) + struct.pack('<H', 0xF900 + 0) # LDA data_l1,Y
    code += bytes([0x9F, 0xC0, 0x64, 0x7F]) # STA.l $7F:64C0,X
    code += bytes([0xE8, 0xE8, 0xC8, 0xC8]) # INX, INX, INY, INY
    code += bytes([0xC0, len(s1_l1)*2])     # CPY #length
    code += bytes([0x90, (loop_l1 - len(code) - 2) & 0xFF]) # BCC loop
    code += bytes([0x60]) # RTS
    
    # Subroutine write_l2
    code_off = len(code)
    snes_addr = 0xF8E3 + code_off
    code[jsr_l2_addr] = snes_addr & 0xFF
    code[jsr_l2_addr+1] = (snes_addr >> 8) & 0xFF
    code += bytes([0xA0, 0x00, 0x00]) # LDY #$0000
    loop_l2 = len(code)
    code += bytes([0xB9]) + struct.pack('<H', 0xF900 + len(s1_l1)*2) # LDA data_l2,Y
    code += bytes([0x9F, 0xC0, 0x64, 0x7F]) # STA.l $7F:64C0,X
    code += bytes([0xE8, 0xE8, 0xC8, 0xC8]) # INX, INX, INY, INY
    code += bytes([0xC0, len(s1_l2)*2])     # CPY #length
    code += bytes([0x90, (loop_l2 - len(code) - 2) & 0xFF]) # BCC loop
    code += bytes([0x60]) # RTS

    # Embed data for Hook 1 (Must be exactly at $83:F900)
    pad = 0xF900 - (0xF8E3 + len(code))
    if pad > 0: code += bytes([0xEA] * pad)
    
    for cid in s1_l1: code += struct.pack('<H', cid)
    for cid in s1_l2: code += struct.pack('<H', cid)

    # Write the payload to $83:F8E3
    off_payload = lorom(0x83, 0xF8E3)
    rom[off_payload:off_payload+len(code)] = code
    
    # Install Hook 1 call at $83:80FF
    off_h1 = lorom(0x83, 0x80FF)
    rom[off_h1:off_h1+4] = bytes([0x22, 0xE3, 0xF8, 0x83]) # JSL $83:F8E3

def main():
    shutil.copyfile('Nage Libre - Seijaku no Suishin (Japan).sfc', 'Nage Libre - Patched.sfc')
    with open('Nage Libre - Patched.sfc', 'r+b') as f:
        rom = bytearray(f.read())
        
        # Step 1: Scan for safe font IDs
        safe_ids = find_safe_ids(rom)
        alloc = ScatterAllocator(safe_ids)
        
        # Parse text table and encode translations
        orig = parse_text_table(rom)
        for s in orig:
            ln = s['line']
            if ln in BANK87_TRANSLATIONS:
                s['translated'] = encode_to_slots(BANK87_TRANSLATIONS[ln], len(s['ids']), alloc)
                
        # Patch text table in place
        for s in orig:
            if 'translated' in s:
                off = s['rom']
                for i, cid in enumerate(s['translated']):
                    struct.pack_into('<H', rom, off + i * 2, cid)
        
        # Encode prologue strings
        s1_l1 = encode_to_slots('  In a far world......', 16, alloc)
        s1_l2 = encode_to_slots('A voice echoes......', 16, alloc)
        s2_l1 = encode_to_slots("  'This world is mine......", 16, alloc)
        s2_l2 = encode_to_slots('Bring the darkness bearers......', 16, alloc)
        
        # Step 2: Install Hook 1 for Screen 1
        install_hook1(rom, s1_l1, s1_l2)
        
        # Step 3: Direct Pointer Patching for Screen 2
        # Write translated prologue strings for Screen 2 to free space in Bank 87
        free_addr = 0xFA0C
        
        def write_string(addr, slot_array):
            off = lorom(0x87, addr)
            for i, cid in enumerate(slot_array):
                struct.pack_into('<H', rom, off + i*2, cid)
            struct.pack_into('<H', rom, off + len(slot_array)*2, 0xFFFF)
            return addr + len(slot_array)*2 + 2

        addr_s2_l1 = free_addr
        free_addr = write_string(addr_s2_l1, s2_l1)
        
        addr_s2_l2 = free_addr
        free_addr = write_string(addr_s2_l2, s2_l2)
        
        # Screen 2, Line 1
        # 87:EA36: LDA #$C5; STA $09; LDA #$89; STA $0A
        rom[lorom(0x87, 0xEA36)+1] = addr_s2_l1 & 0xFF
        rom[lorom(0x87, 0xEA3A)+1] = (addr_s2_l1 >> 8) & 0xFF
        
        # Screen 2, Line 2
        # 87:EA52: LDA #$DF; STA $09; LDA #$89; STA $0A
        rom[lorom(0x87, 0xEA52)+1] = addr_s2_l2 & 0xFF
        rom[lorom(0x87, 0xEA56)+1] = (addr_s2_l2 >> 8) & 0xFF
        
        # Write custom tile graphics back to ROM
        for (cl, cr), cid in alloc.p2id.items():
            td = make_pair_tile(cl, cr)
            off = char_id_to_rom(cid)
            rom[off:off+64] = td

        # Fix checksum
        chk = sum(rom) & 0xFFFF
        chk_off = lorom(0x00, 0xFFDE)
        struct.pack_into('<H', rom, chk_off, chk)
        struct.pack_into('<H', rom, chk_off + 2, chk ^ 0xFFFF)
        
        f.seek(0)
        f.write(rom)
        print("Patched Screen 1 (Hook 1) and Screen 2 (Pointer Patch) successfully!")

if __name__ == '__main__':
    main()
