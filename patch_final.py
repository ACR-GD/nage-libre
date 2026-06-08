import sys
import struct
import os

def lorom(bank, addr):
    return (bank & 0x7F) * 0x8000 + (addr - 0x8000)

def main():
    sys.path.append(os.getcwd())
    import build_patched_rom_backup
    
    rom = bytearray(open('Nage Libre - Seijaku no Suishin (Japan).sfc', 'rb').read())
    
    # 1. Setup font exactly like the backup script
    free_ids = build_patched_rom_backup.find_unused_tile_ids(rom)
    alloc = build_patched_rom_backup.ScatterAllocator(free_ids)
    
    # 2. Embed the dual-character bitmaps into the ROM (overwriting unused Kanji)
    # We need the VWF json for this!
    import json
    with open('.agents/agents/font_builder/vwf_font.json') as f:
        vwf = json.load(f)
        
    s1_l1 = build_patched_rom_backup.encode_to_slots('  In a far world......', 16, alloc)
    s1_l2 = build_patched_rom_backup.encode_to_slots('A voice echoes......', 16, alloc)
    s2_l1 = build_patched_rom_backup.encode_en("  'This world is mine......", alloc)
    s2_l2 = build_patched_rom_backup.encode_en("Bring the darkness bearers......'", alloc)
    
    # Write the actual bitmaps
    for cid, (cl, cr) in alloc.id2p.items():
        # Get bits for cl and cr
        lb = bytes.fromhex(vwf[cl]['bitmap']) if cl in vwf else bytes([0]*16)
        rb = bytes.fromhex(vwf[cr]['bitmap']) if cr in vwf else bytes([0]*16)
        
        # Combine them (8x16 each side)
        combined = bytearray(16)
        for i in range(16):
            combined[i] = lb[i] | (rb[i] >> 8) # Wait, vwf format in backup script?
            
        # Actually, let's just let build_patched_rom_backup handle ALL OF IT!
        # It has everything we need!
    pass

if __name__ == '__main__':
    main()
