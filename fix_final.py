import struct

with open('build_patched_rom.py', 'r') as f:
    content = f.read()

# We will completely replace assemble_hook and the step 6 code with the final correct logic.
import re

new_code = """
def assemble_hooks(alloc):
    # Encode all English lines
    # Screen 1 Line 1
    s1_l1 = encode_to_slots('  In a far world......', 16, alloc)
    # Screen 1 Line 2
    s1_l2 = encode_to_slots('A voice echoes......  ', 16, alloc)
    # Screen 1 Line 3 (blank)
    s1_l3 = [JP_SPACE] * 16
    
    # Screen 2 Line 1 Part A (12 pairs) and B (5 pairs)
    # Original split: 89C5 (12 chars), 89DF (5 chars)
    # Let's split English line 1 into two parts
    # "  'This world is mine......" -> 16 pairs total
    # Let's give 12 pairs to Part A, and 4 pairs + spaces to Part B
    s2_l1 = encode_to_slots("  'This world is mine......", 16, alloc)
    s2_l1a = s2_l1[:12]
    s2_l1b = s2_l1[12:]
    while len(s2_l1b) < 5: s2_l1b.append(JP_SPACE)
    s2_l1b = s2_l1b[:5]
    
    # Screen 2 Line 2 Part A (7 pairs), B (7 pairs), C (5 pairs)
    # "  Bring the darkness bearers......'" -> 16 pairs total
    s2_l2 = encode_to_slots("  Bring the darkness bearers......'", 16, alloc)
    s2_l2a = s2_l2[:7]
    s2_l2b = s2_l2[7:14]
    s2_l2c = s2_l2[14:]
    while len(s2_l2c) < 5: s2_l2c.append(JP_SPACE)
    s2_l2c = s2_l2c[:5]

    HOOK_SNES_BASE = 0xF8E3
    code = bytearray()

    # ==========================================================
    # HOOK 1: WRAM Tilemap Hook (Screen 1 Pre-rendered Background)
    # Hook point: $83:80FF (replaces JSL $80:F8D8)
    # ==========================================================
    hook1_start = len(code)
    code += bytes([0x22, 0xD8, 0xF8, 0x80])   # JSL $80:F8D8 (Call original decompressor)
    code += bytes([0x08, 0x8B, 0xC2, 0x30, 0x48, 0xDA, 0x5A]) # Save state
    code += bytes([0xE2, 0x20, 0xA9, 0x83, 0x48, 0xAB, 0xC2, 0x20]) # Set DBR = $83

    # Check screen 1/3: $7F:6602 == 0x075A
    code += bytes([0xAF, 0x02, 0x66, 0x7F])    # LDA.l $7F:6602
    code += bytes([0xC9, 0x5A, 0x07])           # CMP #$075A
    bne_not_s1 = len(code)
    code += bytes([0xD0, 0x00])                 # BNE not_s1

    # Write Line 1 at offset $0122 (WRAM $7F:65E2)
    code += bytes([0xA2, 0x22, 0x01])           # LDX #$0122
    code += bytes([0x20])                       # JSR write_line1
    jsr_l1_addr = len(code)
    code += bytes([0x00, 0x00])
    
    # Write Line 2 at offset $01A2 (WRAM $7F:6662)
    code += bytes([0xA2, 0xA2, 0x01])           # LDX #$01A2
    code += bytes([0x20])                       # JSR write_line2
    jsr_l2_addr = len(code)
    code += bytes([0x00, 0x00])
    
    # Write Line 3 at offset $0222 (WRAM $7F:66E2)
    code += bytes([0xA2, 0x22, 0x02])           # LDX #$0222
    code += bytes([0x20])                       # JSR write_line3
    jsr_l3_addr = len(code)
    code += bytes([0x00, 0x00])

    not_s1_pos = len(code)
    code[bne_not_s1 + 1] = (not_s1_pos - (bne_not_s1 + 2)) & 0xFF

    code += bytes([0x7A, 0xFA, 0x68, 0xAB, 0x28, 0x6B]) # Restore state and RTL

    # Subroutines for Hook 1
    subs = [(s1_l1, jsr_l1_addr), (s1_l2, jsr_l2_addr), (s1_l3, jsr_l3_addr)]
    s1_data_refs = []
    for string_data, jsr_ref in subs:
        sub_start = len(code)
        sub_snes = HOOK_SNES_BASE + sub_start
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
    # Hook point: $80:F4A7 (replaces JSR $F4AB; RTL)
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
    for _, lda_data_ref in s2_data_refs:
        # We need to fill the BRA skip target for each
        # Wait, I didn't save the BRA offsets! Let's just calculate them backwards
        pass
    
    # Fix BRA skips
    # Actually it's easier to just fix them now:
    bra_offsets = []
    idx = 0
    while idx < len(code):
        if code[idx] == 0x80 and code[idx-2] == 0x85 and code[idx-3] == 0x0B:
            bra_offsets.append(idx)
        idx += 1
    for b in bra_offsets:
        code[b+1] = (skip_pos - (b+2)) & 0xFF
    
    code += bytes([0x28]) # PLP
    # Jump to F4AB
    code += bytes([0x22, 0xAB, 0xF4, 0x80]) # JSL $80:F4AB
    code += bytes([0x6B]) # RTL
    
    # Append terminated strings for Screen 2
    for lda_data_ref, string_data in s2_data_refs:
        str_snes = HOOK_SNES_BASE + len(code)
        code[lda_data_ref+1] = str_snes & 0xFF
        code[lda_data_ref+2] = (str_snes >> 8) & 0xFF
        for cid in string_data:
            code += bytes([cid & 0xFF, (cid >> 8) & 0xFF])
        code += bytes([0xFF, 0xFF]) # TERMINATOR!

    return bytes(code), hook2_snes
"""

new_main = """
def main():
    # Step 1-5 ... same
    with open(ROM_PATH, 'rb') as f:
        rom = bytearray(f.read())
        
    # Find safe IDs
    safe_ids = []
    for i in range(0x1000):
        off = KANJI_ROM_OFFSET + i * 16
        data = rom[off:off+16]
        if all(b == 0 for b in data):
            safe_ids.append(0x1000 + i)
            
    alloc = ScatterAllocator(safe_ids)
    
    # Text table ...
    lines = []
    for addr in TEXT_TABLE_ADDRS:
        lines.append("")
        
    # Encode and patch
    # ... We don't really care about the menu text for the prologue fix, but let's keep it intact
    from build_patched_rom import parse_text_table, patch_text_table, encode_en
    # Wait, it's easier to just run the original script and overwrite assemble_hook in it.
"""

# I will rewrite build_patched_rom.py using replace_file_content to inject the new assemble_hooks
