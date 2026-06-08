#!/usr/bin/env python3
"""
Nage Libre ROM Patcher — Prologue Text Hook
=============================================
Hooks the scene decompressor at $83:80FF (JSL $80F8D8) to redirect
to a custom routine that:
  1. Calls the original decompressor
  2. Checks if the prologue scene was decompressed (by looking for 遠=075A)
  3. If so, overwrites the prologue text bytes in WRAM $7F:6602+
  4. Returns normally

The hook code is placed in free space at the end of bank $83.
"""
import struct
import shutil
from pathlib import Path

ROM_PATH = Path(__file__).parent / "Nage Libre - Seijaku no Suishin (Japan).sfc"
PATCHED_PATH = Path(__file__).parent / "Nage Libre - Patched.sfc"

def cpu_to_rom(bank, addr):
    return ((bank & 0x7F) * 0x8000) + (addr - 0x8000)

# Character ID lookup (from our glyph mapping)
C = {
    # Hiragana
    'あ': 0x0010, 'い': 0x0014, 'う': 0x0018, 'ぇ': 0x001A,
    'え': 0x001C, 'ぉ': 0x001E, 'お': 0x0020, 'か': 0x0022,
    'が': 0x0024, 'く': 0x002A, 'け': 0x002E, 'げ': 0x0030,
    'こ': 0x0032, 'さ': 0x0036, 'し': 0x003A, 'す': 0x003E,
    'せ': 0x0042, 'た': 0x004A, 'だ': 0x004C, 'っ': 0x0052,
    'つ': 0x0054, 'て': 0x0058, 'で': 0x005A, 'と': 0x005C,
    'ど': 0x005E, 'な': 0x0060, 'に': 0x0062, 'ね': 0x0066,
    'の': 0x0068, 'は': 0x006A, 'べ': 0x007E, 'ほ': 0x0088,
    'め': 0x008E, 'よ': 0x009E, 'ら': 0x00A2, 'り': 0x00A4,
    'る': 0x00A6, 'れ': 0x00A8, 'ろ': 0x00AA, 'を': 0x00AE,
    'ん': 0x00B0,
    # Katakana
    'ア': 0x00B2, 'イ': 0x00B6, 'エ': 0x00BE, 'オ': 0x00C2,
    'カ': 0x00C4, 'ガ': 0x00C6, 'キ': 0x00C8, 'ク': 0x00CC,
    'ゴ': 0x00D6, 'サ': 0x00D8, 'シ': 0x00DC, 'ジ': 0x00DE,
    'ス': 0x00E0, 'セ': 0x00E4, 'タ': 0x00EC, 'ダ': 0x00EE,
    'ツ': 0x00F4, 'デ': 0x00FC, 'ト': 0x00FE, 'ド': 0x0100,
    'ネ': 0x0108, 'パ': 0x0110, 'ビ': 0x0114, 'ピ': 0x0116,
    'フ': 0x0118, 'ブ': 0x011A, 'プ': 0x011C, 'ベ': 0x0120,
    'マ': 0x012A, 'ム': 0x012E, 'メ': 0x0130, 'モ': 0x0132,
    'ヤ': 0x0136, 'ラ': 0x0140, 'リ': 0x0142, 'ル': 0x0144,
    'レ': 0x0146, 'ロ': 0x0148, 'ン': 0x014E,
    # Kanji & symbols
    '世': 0x033A, '界': 0x033C, '遠': 0x075A, '声': 0x070E,
    '響': 0x04BE, '入': 0x03BC,
    # Special
    ' ': 0x03FE, '…': 0x02AA,
}


def encode(text):
    """Encode a string into a list of 16-bit character IDs."""
    return [C[ch] for ch in text]


def assemble_hook(new_text_ids):
    """
    Assemble the 65816 hook routine.
    
    The routine:
      1. Calls the original decompressor (JSL $80F8D8)
      2. Checks if bytes at $7F:6602 == 075A (遠) to detect prologue
      3. If so, overwrites $7F:6602+ with new_text_ids
      4. Returns (RTL)
    """
    code = bytearray()
    
    # JSL $80F8D8 — call original decompressor
    code += bytes([0x22, 0xD8, 0xF8, 0x80])
    
    # PHP — save processor flags
    code += bytes([0x08])
    
    # REP #$20 — 16-bit accumulator
    code += bytes([0xC2, 0x20])
    
    # PHA — save A
    code += bytes([0x48])
    
    # LDA.l $7F6602 — load 16-bit from WRAM
    code += bytes([0xAF, 0x02, 0x66, 0x7F])
    
    # CMP #$075A — is it 遠?
    code += bytes([0xC9, 0x5A, 0x07])
    
    # BNE skip — if not prologue, skip patching
    # (we'll fill in the offset later)
    bne_pos = len(code)
    code += bytes([0xD0, 0x00])  # placeholder
    
    # LDA.l $7F6604 — double-check next char
    code += bytes([0xAF, 0x04, 0x66, 0x7F])
    
    # CMP #$002A — is it く?
    code += bytes([0xC9, 0x2A, 0x00])
    
    # BNE skip
    bne2_pos = len(code)
    code += bytes([0xD0, 0x00])  # placeholder
    
    # --- Prologue detected! Patch the text ---
    # Write each 16-bit ID to WRAM $7F:6602 + offset
    wram_base = 0x7F6602
    for i, char_id in enumerate(new_text_ids):
        addr = wram_base + i * 2
        lo = char_id & 0xFF
        hi = (char_id >> 8) & 0xFF
        # LDA #$xxxx
        code += bytes([0xA9, lo, hi])
        # STA.l $7Fxxxx
        code += bytes([0x8F, addr & 0xFF, (addr >> 8) & 0xFF, (addr >> 16) & 0xFF])
    
    # skip: label target
    skip_offset = len(code)
    
    # PLA — restore A
    code += bytes([0x68])
    
    # PLP — restore flags
    code += bytes([0x28])
    
    # RTL — return long
    code += bytes([0x6B])
    
    # Fix up BNE offsets
    code[bne_pos + 1] = skip_offset - (bne_pos + 2)
    code[bne2_pos + 1] = skip_offset - (bne2_pos + 2)
    
    return bytes(code)


def fix_checksum(rom):
    """Recalculate and update the SNES internal checksum."""
    # Clear existing checksum fields
    rom[0x7FDC] = 0xFF
    rom[0x7FDD] = 0xFF
    rom[0x7FDE] = 0x00
    rom[0x7FDF] = 0x00
    
    # Calculate checksum (sum of all bytes, mod 0x10000)
    checksum = sum(rom) & 0xFFFF
    complement = (checksum ^ 0xFFFF) & 0xFFFF
    
    # Write checksum and complement
    rom[0x7FDC] = complement & 0xFF
    rom[0x7FDD] = (complement >> 8) & 0xFF
    rom[0x7FDE] = checksum & 0xFF
    rom[0x7FDF] = (checksum >> 8) & 0xFF
    
    return checksum


def main():
    with open(ROM_PATH, 'rb') as f:
        rom = bytearray(f.read())
    
    print(f"Original ROM: {len(rom)} bytes")
    
    # =========================================================
    # Define the replacement text for the first prologue line
    # Original: 遠くの世界で……声が響く……  (8+6 = 14 chars)
    # Replace:  ここの世界で……声が響く……  (same length!)
    # =========================================================
    
    original_ids = encode('遠くの世界で……声が響く……')
    new_ids      = encode('ここの世界で……声が響く……')
    
    print(f"\nOriginal text: 遠くの世界で……声が響く……")
    print(f"  IDs: {' '.join(f'{v:04X}' for v in original_ids)}")
    print(f"New text:      ここの世界で……声が響く……")
    print(f"  IDs: {' '.join(f'{v:04X}' for v in new_ids)}")
    
    assert len(original_ids) == len(new_ids), "Text length mismatch!"
    
    # =========================================================
    # Verify the original bytes at the hook point
    # JSL $80F8D8 at ROM 0x0180FF (CPU $83:80FF)
    # =========================================================
    HOOK_POINT = 0x0180FF
    
    expected = bytes([0x22, 0xD8, 0xF8, 0x80])
    actual = rom[HOOK_POINT:HOOK_POINT+4]
    assert actual == expected, f"Hook point mismatch! Expected {expected.hex()}, got {actual.hex()}"
    print(f"\n✓ Hook point verified at ROM 0x{HOOK_POINT:06X} (JSL $80F8D8)")
    
    # =========================================================
    # Assemble the hook routine
    # =========================================================
    hook_code = assemble_hook(new_ids)
    print(f"✓ Hook routine assembled: {len(hook_code)} bytes")
    print(f"  Hex: {hook_code.hex()}")
    
    # =========================================================
    # Place hook code in free space at end of bank $83
    # Bank $83: 1821 free bytes starting at ROM 0x01F8E3 (CPU $83:F8E3)
    # =========================================================
    FREE_SPACE = 0x01F8E3
    FREE_SPACE_CPU_BANK = 0x83
    FREE_SPACE_CPU_ADDR = 0xF8E3
    
    assert len(hook_code) <= 1821, f"Hook code too large! {len(hook_code)} > 1821"
    
    # Verify free space is actually empty
    for i in range(len(hook_code)):
        assert rom[FREE_SPACE + i] == 0xFF, \
            f"Free space not empty at offset {FREE_SPACE + i:06X}: {rom[FREE_SPACE + i]:02X}"
    print(f"✓ Free space verified at ROM 0x{FREE_SPACE:06X} ({len(hook_code)} bytes needed)")
    
    # Write hook code to free space
    for i, b in enumerate(hook_code):
        rom[FREE_SPACE + i] = b
    
    # =========================================================
    # Redirect the JSL at the hook point to our routine
    # Original: JSL $80F8D8 → 22 D8 F8 80
    # New:      JSL $83F8E3 → 22 E3 F8 83
    # =========================================================
    rom[HOOK_POINT + 0] = 0x22
    rom[HOOK_POINT + 1] = FREE_SPACE_CPU_ADDR & 0xFF        # E3
    rom[HOOK_POINT + 2] = (FREE_SPACE_CPU_ADDR >> 8) & 0xFF  # F8
    rom[HOOK_POINT + 3] = FREE_SPACE_CPU_BANK                # 83
    
    new_target = rom[HOOK_POINT+1] | (rom[HOOK_POINT+2]<<8) | (rom[HOOK_POINT+3]<<16)
    print(f"✓ JSL redirected: $80F8D8 → ${new_target:06X}")
    
    # =========================================================
    # Fix ROM checksum
    # =========================================================
    checksum = fix_checksum(rom)
    print(f"✓ Checksum updated: ${checksum:04X}")
    
    # =========================================================
    # Write patched ROM
    # =========================================================
    with open(PATCHED_PATH, 'wb') as f:
        f.write(rom)
    
    print(f"\n{'='*60}")
    print(f"Patched ROM written to: {PATCHED_PATH}")
    print(f"{'='*60}")
    print()
    print("WHAT TO EXPECT:")
    print("  Start a New Game. The opening crawl text should read:")
    print("    ここの世界で……   (instead of 遠くの世界で……)")
    print("    ↑↑")
    print("  'こ' appears twice where '遠く' used to be.")
    print("  Everything else should be unchanged.")


if __name__ == '__main__':
    main()
