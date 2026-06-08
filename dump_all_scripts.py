#!/usr/bin/env python3
"""
Nage Libre Script Dumper
========================
Extracts all text script pointers from the ROM and dumps them.

The text engine works as follows:
1. Code sets ZP $09/$0A/$0B to a 24-bit pointer (bank:hi:lo) pointing to script data
2. Calls JSL $80F4A7 (simple text display) or JSL $80F4CE (complex with control codes)
3. The script data is an array of 16-bit character IDs, terminated by $FFFF
4. Control code $03FE appears to mark special behavior (newlines, etc.)
5. IDs >= $0010 are kanji/characters, IDs < $0010 are control codes

Memory mapping: LoROM (map mode $30)
  ROM offset = ((bank & 0x7F) * 0x8000) + (address - 0x8000)
"""

import struct
import csv
import sys
from pathlib import Path

ROM_PATH = Path(__file__).parent / "Nage Libre - Seijaku no Suishin (Japan).sfc"
GLYPH_CSV = Path(__file__).parent / "docs" / "glyph_mapping_wip.csv"

def cpu_to_rom(bank, addr):
    """Convert SNES LoROM CPU address to ROM file offset."""
    return ((bank & 0x7F) * 0x8000) + (addr - 0x8000)

def rom_to_cpu(offset):
    """Convert ROM file offset to SNES LoROM CPU address."""
    bank = (offset // 0x8000) + 0x80
    addr = (offset % 0x8000) + 0x8000
    return bank, addr

def load_glyph_table():
    """Load the glyph mapping CSV to translate IDs to characters."""
    table = {}
    if not GLYPH_CSV.exists():
        return table
    with open(GLYPH_CSV, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        header = None
        for row in reader:
            if header is None:
                header = row
                continue
            if len(row) < 3:
                continue
            code_hex = row[0].strip()
            char = row[2].strip()  # 'character' is column index 2
            if not char:
                continue
            try:
                # Handle Excel corruption like "1E+02", "0E+00" (scientific notation)
                if '+' in code_hex:
                    # Use the decimal column instead
                    glyph_id = int(row[1].strip())
                else:
                    glyph_id = int(code_hex, 16)
                table[glyph_id] = char
            except (ValueError, IndexError):
                continue
    return table

def find_all_script_pointers(rom):
    """
    Find all places in ROM where ZP $09/$0A/$0B are set up with a script pointer
    followed by JSL $80F4A7.
    
    Pattern: E2 20 ... A9 xx 85 09 A9 yy 85 0A A9 zz 85 0B ... 22 A7 F4 80
    Simpler pattern: A9 xx 85 09 A9 yy 85 0A A9 zz 85 0B
    """
    pointers = []
    seen = set()
    
    for i in range(len(rom) - 12):
        # Look for: A9 xx 85 09 A9 yy 85 0A A9 zz 85 0B
        if (rom[i] == 0xA9 and rom[i+2] == 0x85 and rom[i+3] == 0x09 and
            rom[i+4] == 0xA9 and rom[i+6] == 0x85 and rom[i+7] == 0x0A and
            rom[i+8] == 0xA9 and rom[i+10] == 0x85 and rom[i+11] == 0x0B):
            
            lo = rom[i+1]
            hi = rom[i+5]
            bank = rom[i+9]
            
            script_cpu = (bank << 16) | (hi << 8) | lo
            if script_cpu in seen:
                continue
            
            # Validate: bank should be reasonable (80-FF for LoROM)
            if bank < 0x80:
                continue
            addr = (hi << 8) | lo
            if addr < 0x8000:
                continue
                
            rom_off = cpu_to_rom(bank, addr)
            if rom_off < 0 or rom_off >= len(rom) - 2:
                continue
            
            # Check that the data looks like script (array of 16-bit values)
            # First value should be a valid character ID or FFFF
            first_val = rom[rom_off] | (rom[rom_off+1] << 8)
            if first_val > 0x1000 and first_val != 0xFFFF and first_val != 0x03FE:
                continue
            
            caller_bank, caller_addr = rom_to_cpu(i)
            
            seen.add(script_cpu)
            pointers.append({
                'caller_cpu': f"${caller_bank:02X}:{caller_addr:04X}",
                'caller_rom': i,
                'script_cpu': f"${bank:02X}:{addr:04X}",
                'script_rom': rom_off,
                'bank': bank,
                'addr': addr,
            })
    
    return sorted(pointers, key=lambda p: p['script_rom'])

def read_script(rom, rom_offset, max_words=500):
    """Read a script from ROM starting at the given offset.
    Returns a list of lines, where each line is a list of 16-bit character IDs."""
    lines = []
    current_line = []
    
    pos = rom_offset
    for _ in range(max_words):
        if pos + 1 >= len(rom):
            break
        val = rom[pos] | (rom[pos+1] << 8)
        pos += 2
        
        if val == 0xFFFF:
            lines.append(current_line)
            current_line = []
            # Check if next value exists and is also FFFF (double terminator = end of text block)
            if pos + 1 < len(rom):
                next_val = rom[pos] | (rom[pos+1] << 8)
                # Heuristic: if we see lots of 03FE (padding) or another FFFF, keep going
                # But if we see something that doesn't look like a char ID, stop
                if next_val > 0x1000 and next_val != 0xFFFF and next_val != 0x03FE:
                    break
        else:
            current_line.append(val)
    
    if current_line:
        lines.append(current_line)
    
    # Remove trailing empty lines
    while lines and not lines[-1]:
        lines.pop()
    
    return lines

def translate_line(char_ids, glyph_table):
    """Translate a list of character IDs to text using the glyph table."""
    result = []
    for cid in char_ids:
        if cid == 0x03FE:
            result.append(' ')  # Padding/blank
        elif cid == 0x0346:
            result.append('　')  # Ideographic space
        elif cid == 0x02E0:
            result.append('‼')
        elif cid == 0x02FA:
            result.append('、')
        elif cid == 0x02AA:
            result.append('…')
        elif cid in glyph_table:
            result.append(glyph_table[cid])
        else:
            result.append(f'[{cid:04X}]')
    return ''.join(result)

def main():
    with open(ROM_PATH, 'rb') as f:
        rom = f.read()
    
    print(f"ROM size: {len(rom)} bytes ({len(rom) / 1024:.0f} KB)")
    
    glyph_table = load_glyph_table()
    print(f"Loaded {len(glyph_table)} glyph mappings")
    
    pointers = find_all_script_pointers(rom)
    print(f"Found {len(pointers)} unique script pointers\n")
    
    all_scripts = []
    
    for p in pointers:
        lines = read_script(rom, p['script_rom'])
        if not lines:
            continue
        
        print(f"=== Script at {p['script_cpu']} (ROM 0x{p['script_rom']:06X}) ===")
        print(f"    Called from: {p['caller_cpu']}")
        
        for line_idx, line in enumerate(lines):
            hex_str = ' '.join(f'{v:04X}' for v in line)
            text = translate_line(line, glyph_table)
            print(f"  Line {line_idx}: {text}")
            print(f"         IDs: {hex_str}")
        print()
        
        all_scripts.append({
            'address': p['script_cpu'],
            'rom_offset': p['script_rom'],
            'caller': p['caller_cpu'],
            'lines': lines,
        })
    
    # Save to CSV
    output_csv = Path(__file__).parent / "docs" / "extracted_scripts.csv"
    output_csv.parent.mkdir(exist_ok=True)
    
    with open(output_csv, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Script Address', 'ROM Offset', 'Caller', 'Line', 'Hex IDs', 'Translated Text'])
        
        for script in all_scripts:
            for line_idx, line in enumerate(script['lines']):
                hex_str = ' '.join(f'{v:04X}' for v in line)
                text = translate_line(line, glyph_table)
                writer.writerow([
                    script['address'],
                    f"0x{script['rom_offset']:06X}",
                    script['caller'],
                    line_idx,
                    hex_str,
                    text,
                ])
    
    print(f"\nSaved {len(all_scripts)} scripts to {output_csv}")

if __name__ == '__main__':
    main()
