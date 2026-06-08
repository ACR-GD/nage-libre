import struct
import os
import json

def lorom(bank, addr):
    return (bank & 0x7F) * 0x8000 + (addr - 0x8000)

def char_id_to_rom(cid):
    a = ((cid * 32) + 0x8000) & 0xFFFF
    if a >= 0x8000:
        return ((0x85 & 0x7F) * 0x8000) + (a - 0x8000)
    return ((0x86 & 0x7F) * 0x8000) + a

def _rows_to_2bpp(rows):
    tile = bytearray(16)
    for i, p in enumerate(rows):
        tile[i*2] = p       # bp0 = pixel -> color 1 = white
        tile[i*2+1] = 0x00  # bp1 = 0
    return bytes(tile)

def find_safe_ids(rom):
    blank = set()
    for cid in range(0x0800):
        off = char_id_to_rom(cid)
        if all(b == 0 for b in rom[off:off+64]):
            blank.add(cid)
    
    referenced = set()
    i = 0x038697
    while i < 0x038C01:
        w = rom[i] | (rom[i+1] << 8)
        if w != 0xFFFF and w < 0x0800: referenced.add(w)
        i += 2
        
    for x in [0x03FE, 0x03FF, 0x02AA, 0x02AB, 0x02E0, 0x02E1]: referenced.add(x)
    
    safe = sorted(n for n in blank if n % 2 == 0 and (n+1) in blank and n not in referenced and (n+1) not in referenced)
    semi = sorted(n for n in blank if n % 2 == 0 and (n+1) not in blank and n not in referenced and (n+1) not in referenced)
    tier1_2 = set(safe + semi)
    extended = sorted(n for n in range(0x0100, 0x0800, 2) if n not in tier1_2 and n not in referenced and (n+1) not in referenced)
    
    return safe + semi + extended

class ScatterAllocator:
    def __init__(self, free_ids):
        self.free = list(free_ids)
        self.idx = 0
        self.p2id = {}
        self.id2p = {}
    
    def get(self, cl, cr):
        k = (cl, cr)
        if k not in self.p2id:
            cid = self.free[self.idx]
            self.idx += 1
            self.p2id[k] = cid
            self.id2p[cid] = k
        return self.p2id[k]

def encode_en(text, alloc):
    ids = []
    chars = list(text)
    i = 0
    while i < len(chars):
        cl = chars[i]
        cr = chars[i+1] if i+1 < len(chars) else ' '
        ids.append(alloc.get(cl, cr))
        i += 2
    return ids

def encode_to_slots(text, slot_count, alloc):
    ids = encode_en(text, alloc)
    while len(ids) < slot_count:
        ids.append(alloc.get(' ', ' '))
    return ids[:slot_count]

def make_pair_tile(cl, cr):
    import build_patched_rom_backup
    FONT = build_patched_rom_backup.FONT
    
    lt, lb = FONT.get(cl, FONT[' '])
    rt, rb = FONT.get(cr, FONT[' '])
    
    # Pack rows into 2bpp
    tile = bytearray(64)
    # top-left 8x8
    for i, p in enumerate(lt):
        tile[i*2] = p; tile[i*2+1] = 0
    # top-right 8x8
    for i, p in enumerate(rt):
        tile[16 + i*2] = p; tile[16 + i*2+1] = 0
    # bottom-left 8x8
    for i, p in enumerate(lb):
        tile[32 + i*2] = p; tile[32 + i*2+1] = 0
    # bottom-right 8x8
    for i, p in enumerate(rb):
        tile[48 + i*2] = p; tile[48 + i*2+1] = 0
        
    return bytes(tile)

def install_hook1(rom, s1_l1, s1_l2):
    code = bytearray()
    code += bytes([0x22, 0xD8, 0xF8, 0x80]) # JSL $80:F8D8
    code += bytes([0x08, 0x8B, 0xC2, 0x30, 0x48, 0xDA, 0x5A]) # PHP, PHB, REP #$30, PHA, PHX, PHY
    code += bytes([0xE2, 0x20, 0xA9, 0x83, 0x48, 0xAB, 0xC2, 0x20]) # SEP #$20, LDA #$83, PHA, PLB, REP #$20
    code += bytes([0xA2, 0x22, 0x01, 0x20, 0x00, 0x00]) # LDX #$0122, JSR write_l1
    jsr_l1_addr = len(code) - 2
    code += bytes([0xA2, 0x66, 0x01, 0x20, 0x00, 0x00]) # LDX #$0166, JSR write_l2
    jsr_l2_addr = len(code) - 2
    code += bytes([0x7A, 0xFA, 0x68, 0xAB, 0x28, 0x6B]) # PLY, PLX, PLA, PLB, PLP, RTL
    
    code_off = len(code)
    snes_addr = 0xF8E3 + code_off
    code[jsr_l1_addr] = snes_addr & 0xFF
    code[jsr_l1_addr+1] = (snes_addr >> 8) & 0xFF
    code += bytes([0xA0, 0x00, 0x00])
    loop_l1 = len(code)
    code += bytes([0xB9]) + struct.pack('<H', 0xF900 + 0)
    code += bytes([0x9F, 0xC0, 0x64, 0x7F])
    code += bytes([0xE8, 0xE8, 0xC8, 0xC8])
    code += bytes([0xC0, len(s1_l1)*2])
    code += bytes([0x90, (loop_l1 - len(code) - 2) & 0xFF])
    code += bytes([0x60])
    
    code_off = len(code)
    snes_addr = 0xF8E3 + code_off
    code[jsr_l2_addr] = snes_addr & 0xFF
    code[jsr_l2_addr+1] = (snes_addr >> 8) & 0xFF
    code += bytes([0xA0, 0x00, 0x00])
    loop_l2 = len(code)
    code += bytes([0xB9]) + struct.pack('<H', 0xF900 + len(s1_l1)*2)
    code += bytes([0x9F, 0xC0, 0x64, 0x7F])
    code += bytes([0xE8, 0xE8, 0xC8, 0xC8])
    code += bytes([0xC0, len(s1_l2)*2])
    code += bytes([0x90, (loop_l2 - len(code) - 2) & 0xFF])
    code += bytes([0x60])

    pad = 0xF900 - (0xF8E3 + len(code))
    if pad > 0: code += bytes([0xEA] * pad)
    
    for cid in s1_l1: code += struct.pack('<H', cid)
    for cid in s1_l2: code += struct.pack('<H', cid)

    off_payload = lorom(0x83, 0xF8E3)
    rom[off_payload:off_payload+len(code)] = code
    off_h1 = lorom(0x83, 0x80FF)
    rom[off_h1:off_h1+4] = bytes([0x22, 0xE3, 0xF8, 0x83])

def main():
    if not os.path.exists('Nage Libre - Seijaku no Suishin (Japan).sfc'): return
    rom = bytearray(open('Nage Libre - Seijaku no Suishin (Japan).sfc', 'rb').read())
    
    free_ids = find_safe_ids(rom)
    alloc = ScatterAllocator(free_ids)
    
    # Encode Screen 1 text
    s1_l1 = encode_to_slots('  In a far world......', 16, alloc)
    s1_l2 = encode_to_slots('A voice echoes......', 16, alloc)

    # Encode Screen 2 text
    s2_line1_text = " 'This world is mine"
    s2_line1_ids = encode_en(s2_line1_text, alloc)
    while len(s2_line1_ids) < 12: s2_line1_ids.append(alloc.get(' ', ' '))
    s2_line1_ids = s2_line1_ids[:12]

    s2_line1b_text = "......'"
    s2_line1b_ids = encode_en(s2_line1b_text, alloc)
    while len(s2_line1b_ids) < 5: s2_line1b_ids.append(alloc.get(' ', ' '))
    s2_line1b_ids = s2_line1b_ids[:5]

    s2_line2_text = " Bring the darkness bearers......'"
    s2_line2_ids = encode_en(s2_line2_text, alloc)
    
    s2_line2_a = s2_line2_ids[:7]
    s2_line2_b = s2_line2_ids[7:14]
    s2_line2_c = s2_line2_ids[14:19]
    while len(s2_line2_a) < 7: s2_line2_a.append(alloc.get(' ', ' '))
    while len(s2_line2_b) < 7: s2_line2_b.append(alloc.get(' ', ' '))
    while len(s2_line2_c) < 5: s2_line2_c.append(alloc.get(' ', ' '))

    # Patch Screen 2 in-place
    off_s1a = 0x0389C5
    for i, cid in enumerate(s2_line1_ids):
        struct.pack_into('<H', rom, off_s1a + i * 2, cid)
        
    off_s1b = 0x0389DF
    for i, cid in enumerate(s2_line1b_ids):
        struct.pack_into('<H', rom, off_s1b + i * 2, cid)

    off_s2a = 0x038A51
    for i, cid in enumerate(s2_line2_a):
        struct.pack_into('<H', rom, off_s2a + i * 2, cid)

    off_s2b = 0x038A61
    for i, cid in enumerate(s2_line2_b):
        struct.pack_into('<H', rom, off_s2b + i * 2, cid)

    off_s2c = 0x038A71
    for i, cid in enumerate(s2_line2_c):
        struct.pack_into('<H', rom, off_s2c + i * 2, cid)

    # WRITE THE BITMAPS!
    for (cl, cr), cid in alloc.p2id.items():
        td = make_pair_tile(cl, cr)
        off = char_id_to_rom(cid)
        rom[off:off+64] = td
        
    install_hook1(rom, s1_l1, s1_l2)
    
    open('Nage Libre - Patched.sfc', 'wb').write(rom)
    print("Patched Screen 1 (Hook) and Screen 2 (In-Place) successfully with ScatterAllocator!")

if __name__ == '__main__':
    main()
