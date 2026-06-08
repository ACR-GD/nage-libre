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
        
        # Write translated prologue strings to free space in Bank 87
        free_addr = 0xFA0C
        
        def write_string(addr, slot_array):
            off = lorom(0x87, addr)
            for i, cid in enumerate(slot_array):
                struct.pack_into('<H', rom, off + i*2, cid)
            struct.pack_into('<H', rom, off + len(slot_array)*2, 0xFFFF)
            return addr + len(slot_array)*2 + 2

        addr_s1_l1 = free_addr
        free_addr = write_string(addr_s1_l1, s1_l1)
        
        addr_s1_l2 = free_addr
        free_addr = write_string(addr_s1_l2, s1_l2)
        
        addr_s2_l1 = free_addr
        free_addr = write_string(addr_s2_l1, s2_l1)
        
        addr_s2_l2 = free_addr
        free_addr = write_string(addr_s2_l2, s2_l2)
        
        print(f"Wrote prologue strings to 87:FA0C - 87:{free_addr:04X}")
        
        # Update hardcoded pointers in Bank 87
        
        # Screen 1, Line 1
        # 87:D3C7: LDA #$2F; STA $09; LDA #$89; STA $0A
        rom[lorom(0x87, 0xD3C7)+1] = addr_s1_l1 & 0xFF
        rom[lorom(0x87, 0xD3CB)+1] = (addr_s1_l1 >> 8) & 0xFF
        
        # Screen 1, Line 2
        # 87:D3EE: LDA #$49; STA $09; LDA #$89; STA $0A
        rom[lorom(0x87, 0xD3EE)+1] = addr_s1_l2 & 0xFF
        rom[lorom(0x87, 0xD3F2)+1] = (addr_s1_l2 >> 8) & 0xFF
        
        # Screen 2, Line 1
        # 87:EA36: LDA #$C5; STA $09; LDA #$89; STA $0A
        rom[lorom(0x87, 0xEA36)+1] = addr_s2_l1 & 0xFF
        rom[lorom(0x87, 0xEA3A)+1] = (addr_s2_l1 >> 8) & 0xFF
        
        # Screen 2, Line 2
        # 87:EA52: LDA #$DF; STA $09; LDA #$89; STA $0A
        rom[lorom(0x87, 0xEA52)+1] = addr_s2_l2 & 0xFF
        rom[lorom(0x87, 0xEA56)+1] = (addr_s2_l2 >> 8) & 0xFF
        
        print("Updated hardcoded pointers in Bank 87.")
        
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

if __name__ == '__main__':
    main()
