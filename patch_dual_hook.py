import struct
import shutil
from build_patched_rom import (
    ROM_PATH, KANJI_ROM_OFFSET, JP_SPACE, TEXT_TABLE_ADDRS,
    ScatterAllocator, parse_text_table, encode_en, patch_text_table, lorom
)

def encode_to_slots(text_en, length, alloc):
    padded = text_en.ljust(length, ' ')
    ids = []
    for c in padded:
        if c == ' ': ids.append(JP_SPACE)
        else: ids.append(alloc.allocate_pair(c))
    return ids

def assemble_hooks(alloc):
    # Screen 1
    s1_l1 = encode_to_slots('  In a far world......', 16, alloc)
    s1_l2 = encode_to_slots('A voice echoes......  ', 16, alloc)
    s1_l3 = [JP_SPACE] * 16

    # Screen 2 Line 1 Part A (12 pairs) and B (5 pairs)
    s2_l1 = encode_to_slots("  'This world is mine......", 16, alloc)
    s2_l1a = s2_l1[:12]
    s2_l1b = s2_l1[12:]
    while len(s2_l1b) < 5: s2_l1b.append(JP_SPACE)
    s2_l1b = s2_l1b[:5]
    
    # Screen 2 Line 2 Part A (7 pairs), B (7 pairs), C (5 pairs)
    s2_l2 = encode_to_slots("  Bring the darkness bearers......'", 19, alloc)
    s2_l2a = s2_l2[:7]
    s2_l2b = s2_l2[7:14]
    s2_l2c = s2_l2[14:]
    while len(s2_l2c) < 5: s2_l2c.append(JP_SPACE)
    s2_l2c = s2_l2c[:5]

    HOOK_SNES_BASE = 0xF8E3
    code = bytearray()

    # ==========================================================
    # HOOK 1: WRAM Tilemap Hook (Screen 1)
    # Replaces JSL $80:F8D8 at 83:80FF
    # ==========================================================
    hook1_start = len(code)
    code += bytes([0x22, 0xD8, 0xF8, 0x80])   # JSL $80:F8D8
    code += bytes([0x08, 0x8B, 0xC2, 0x30, 0x48, 0xDA, 0x5A]) # PHP, PHB, REP #30, PHA, PHX, PHY
    code += bytes([0xE2, 0x20, 0xA9, 0x83, 0x48, 0xAB, 0xC2, 0x20]) # Set DBR = $83

    code += bytes([0xAF, 0x02, 0x66, 0x7F])    # LDA.l $7F:6602
    code += bytes([0xC9, 0x5A, 0x07])           # CMP #$075A
    bne_not_s1 = len(code)
    code += bytes([0xD0, 0x00])                 # BNE not_s1

    # Call subroutines to write lines
    code += bytes([0xA2, 0x22, 0x01, 0x20, 0x00, 0x00]) # LDX #$0122, JSR write_l1
    jsr_l1_addr = len(code) - 2
    code += bytes([0xA2, 0xA2, 0x01, 0x20, 0x00, 0x00]) # LDX #$01A2, JSR write_l2
    jsr_l2_addr = len(code) - 2
    code += bytes([0xA2, 0x22, 0x02, 0x20, 0x00, 0x00]) # LDX #$0222, JSR write_l3
    jsr_l3_addr = len(code) - 2

    not_s1_pos = len(code)
    code[bne_not_s1 + 1] = (not_s1_pos - (bne_not_s1 + 2)) & 0xFF

    code += bytes([0x7A, 0xFA, 0x68, 0xAB, 0x28, 0x6B]) # PLY, PLX, PLA, PLB, PLP, RTL

    # Data writing subroutines
    subs = [(s1_l1, jsr_l1_addr), (s1_l2, jsr_l2_addr), (s1_l3, jsr_l3_addr)]
    s1_data_refs = []
    for string_data, jsr_ref in subs:
        sub_snes = HOOK_SNES_BASE + len(code)
        code[jsr_ref] = sub_snes & 0xFF
        code[jsr_ref+1] = (sub_snes >> 8) & 0xFF
        
        code += bytes([0x5A, 0xA0, 0x00, 0x00]) # PHY, LDY #$0000
        loop_top = len(code)
        data_ref = len(code)
        code += bytes([0xB9, 0x00, 0x00])       # LDA data_table,Y
        code += bytes([0x9F, 0xC0, 0x64, 0x7F]) # STA.l $7F:64C0,X
        code += bytes([0xE8, 0xE8, 0xC8, 0xC8]) # INX, INX, INY, INY
        code += bytes([0xC0, 32, 0x00])         # CPY #32
        bcc_loop = len(code)
        code += bytes([0x90, (loop_top - (bcc_loop + 2)) & 0xFF]) # BCC loop_top
        code += bytes([0x7A, 0x60])             # PLY, RTS
        s1_data_refs.append((string_data, data_ref))

    for string_data, data_ref in s1_data_refs:
        data_snes = HOOK_SNES_BASE + len(code)
        code[data_ref+1] = data_snes & 0xFF
        code[data_ref+2] = (data_snes >> 8) & 0xFF
        for cid in string_data:
            code += bytes([cid & 0xFF, (cid >> 8) & 0xFF])

    # ==========================================================
    # HOOK 2: Dynamic String Hook (Screen 2)
    # Replaces JSR $F4AB at 80:F4A7
    # ==========================================================
    hook2_start = len(code)
    hook2_snes = HOOK_SNES_BASE + hook2_start
    
    code += bytes([0x08, 0xC2, 0x20]) # PHP, REP #$20
    
    # Check bank ($0B) == 87
    code += bytes([0xA5, 0x0B])       # LDA $0B
    code += bytes([0x29, 0xFF, 0x00]) # AND #$00FF
    code += bytes([0xC9, 0x87, 0x00]) # CMP #$0087
    bne_skip = len(code)
    code += bytes([0xD0, 0x00])       # BNE skip
    
    code += bytes([0xA5, 0x09])       # LDA $09
    
    s2_targets = [
        (0x89C5, s2_l1a),
        (0x89DF, s2_l1b),
        (0x8A51, s2_l2a),
        (0x8A61, s2_l2b),
        (0x8A71, s2_l2c)
    ]
    
    s2_data_refs = []
    
    for addr, string_data in s2_targets:
        code += bytes([0xC9, addr & 0xFF, (addr >> 8) & 0xFF]) # CMP #addr
        bne_next = len(code)
        code += bytes([0xD0, 0x00]) # BNE next
        
        # Match! Set pointer to our string!
        lda_data_ref = len(code)
        code += bytes([0xA9, 0x00, 0x00]) # LDA #new_addr
        code += bytes([0x85, 0x09])       # STA $09
        code += bytes([0xA9, 0x83, 0x00]) # LDA #$0083
        code += bytes([0x85, 0x0B])       # STA $0B
        bra_skip = len(code)
        code += bytes([0x80, 0x00])       # BRA skip
        
        next_pos = len(code)
        code[bne_next+1] = (next_pos - (bne_next+2)) & 0xFF
        
        s2_data_refs.append((lda_data_ref, string_data))
        
    skip_pos = len(code)
    code[bne_skip+1] = (skip_pos - (bne_skip+2)) & 0xFF
    
    # Fix BRA skip offsets
    for i in range(hook2_start, skip_pos):
        if code[i] == 0x80 and code[i-2] == 0x85 and code[i-3] == 0x0B:
            code[i+1] = (skip_pos - (i+2)) & 0xFF
    
    code += bytes([0x28]) # PLP
    code += bytes([0x22, 0xAB, 0xF4, 0x80]) # JSL $80:F4AB
    code += bytes([0x6B]) # RTL
    
    # Write terminated strings
    for lda_data_ref, string_data in s2_data_refs:
        str_snes = HOOK_SNES_BASE + len(code)
        code[lda_data_ref+1] = str_snes & 0xFF
        code[lda_data_ref+2] = (str_snes >> 8) & 0xFF
        for cid in string_data:
            code += bytes([cid & 0xFF, (cid >> 8) & 0xFF])
        code += bytes([0xFF, 0xFF]) # TERMINATOR!

    return bytes(code), hook2_snes

def main():
    print("--- Step 1: Initialization ---")
    with open(ROM_PATH, 'rb') as f:
        rom = bytearray(f.read())
        
    safe_ids = []
    for i in range(0x1000):
        off = KANJI_ROM_OFFSET + i * 16
        data = rom[off:off+16]
        if all(b == 0 for b in data):
            safe_ids.append(0x1000 + i)
            
    alloc = ScatterAllocator(safe_ids)
    print(f"  Safe font IDs found: {len(safe_ids)}")
    
    print("--- Step 2: Parsing & Patching Menu Text ---")
    strings = parse_text_table(rom)
    patch_text_table(rom, strings, alloc)
    
    print("--- Step 3: Injecting Dual-Hook Architecture ---")
    code_bytes, hook2_snes = assemble_hooks(alloc)
    
    # Write the payload to $83:F8E3
    off_payload = lorom(0x83, 0xF8E3)
    rom[off_payload:off_payload+len(code_bytes)] = code_bytes
    print(f"  Payload written: {len(code_bytes)} bytes at $83:F8E3")
    
    # Install Hook 1 (Screen 1 stamper) at $83:80FF
    off_h1 = lorom(0x83, 0x80FF)
    rom[off_h1:off_h1+4] = bytes([0x22, 0xE3, 0xF8, 0x83]) # JSL $83:F8E3
    print(f"  Hook 1 installed at $83:80FF")

    # Install Hook 2 (Screen 2 dynamic redirector) at $80:F4A7
    off_h2 = lorom(0x80, 0xF4A7)
    rom[off_h2:off_h2+4] = bytes([0x22, hook2_snes & 0xFF, (hook2_snes >> 8) & 0xFF, 0x83]) # JSL $83:xxxx
    print(f"  Hook 2 installed at $80:F4A7 -> $83:{hook2_snes:04X}")

    # Write fonts
    for pair_id, font_data in alloc.pair_to_font.items():
        rom_off = KANJI_ROM_OFFSET + (pair_id - 0x1000) * 16
        rom[rom_off:rom_off+16] = font_data

    # Fix checksum
    rom[0x7FDC:0x7FDE] = b'\xFF\xFF'
    rom[0x7FDE:0x7FE0] = b'\xFF\xFF'
    csum = sum(rom) & 0xFFFF
    struct.pack_into('<H', rom, 0x7FDE, csum)
    struct.pack_into('<H', rom, 0x7FDC, csum ^ 0xFFFF)
    
    out_path = 'Nage Libre - Patched.sfc'
    with open(out_path, 'wb') as f:
        f.write(rom)
    print(f"  Checksum: ${csum:04X}")
    print(f"  Saved to {out_path}")

if __name__ == '__main__':
    main()
