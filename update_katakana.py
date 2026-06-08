import os

def hira_to_kata(c):
    code = ord(c)
    if 0x3041 <= code <= 0x3096:
        return chr(code + 0x60)
    return c

def main():
    workspace_dir = '/Users/acr/Develop/nage-libre'
    index_path = os.path.join(workspace_dir, 'docs', 'glyph_index.csv')
    unicode_path = os.path.join(workspace_dir, 'docs', 'glyph_unicode.csv')
    
    # 1. Load glyph_index.csv metadata
    index_data = {}
    with open(index_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    for line in lines[1:]:
        if not line.strip():
            continue
        parts = line.strip().split(',')
        if len(parts) >= 5:
            byte_hex = parts[0].strip()
            vram_hex = parts[1].strip()
            rom_offset = parts[4].strip()
            byte_val = int(byte_hex, 16)
            index_data[byte_val] = {
                'vram_tile_hex': vram_hex,
                'rom_offset': rom_offset
            }

    # 2. Define Hiragana dialogue characters list (96 characters)
    dialogue_chars = []
    # 0x08 to 0x20
    for c in "がぎぐげござじずぜぞだぢづでどばびぶべぼぱぴぷぺぽ":
        dialogue_chars.append(c)
    # 0x21 to 0x2A
    for c in "ぁぃぅぇぉっゃゅょゎ":
        dialogue_chars.append(c)
    # 0x2B
    dialogue_chars.append("ゔ")
    # 0x2C to 0x59
    for c in "あいうえおかきくけこさしすせそたちつてとなにぬねのはひふへほまみむめもやゆよらりるれろわをん":
        dialogue_chars.append(c)
    # 0x5A to 0x67
    for c in ["ー", "゛", "゜", "？", "！", "。", "「", "」", "・", "事", "見", "言", "思", "、"]:
        dialogue_chars.append(c)

    # 3. Read existing mappings in glyph_unicode.csv to preserve
    existing_entries = {}
    if os.path.exists(unicode_path):
        with open(unicode_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        for line in lines[1:]:
            if not line.strip():
                continue
            parts = line.strip().split(',')
            if len(parts) >= 7:
                byte_hex = parts[0].strip()
                vram_hex = parts[1].strip()
                unicode_hex = parts[2].strip()
                character = parts[3].strip()
                rom_offset = parts[4].strip()
                category = parts[5].strip()
                mapping_source = parts[6].strip()
                
                byte_val = int(byte_hex, 16)
                existing_entries[byte_val] = {
                    'text_byte_hex': byte_hex,
                    'vram_tile_hex': vram_hex,
                    'unicode_hex': unicode_hex,
                    'character': character,
                    'rom_offset': rom_offset,
                    'category': category,
                    'mapping_source': mapping_source
                }

    # 4. Generate Katakana dialogue entries (range 0x88 to 0xE7)
    katakana_entries = {}
    for i, hira_char in enumerate(dialogue_chars):
        byte_val = 0x88 + i
        byte_hex = f"0x{byte_val:02X}"
        kata_char = hira_to_kata(hira_char)
        
        vram_tile_hex = index_data[byte_val]['vram_tile_hex'] if byte_val in index_data else f"0x{0x183 + i:03X}"
        # For rom offset, let's use the actual Katakana Dialogue Font offset if we want, or from index_data.
        # The Katakana Dialogue Font is at: top 0x29810, bottom 0x29E10.
        # Since each character top and bottom are combined, let's put the top offset: 0x029810 + i * 16
        rom_offset = f"0x{0x029810 + i * 16:06X}"
        unicode_hex = f"U+{ord(kata_char):04X}"
        
        katakana_entries[byte_val] = {
            'text_byte_hex': byte_hex,
            'vram_tile_hex': vram_tile_hex,
            'unicode_hex': unicode_hex,
            'character': kata_char,
            'rom_offset': rom_offset,
            'category': 'dialogue_font_katakana',
            'mapping_source': 'dialogue_font_mapping_kata'
        }

    # 5. Merge, overwriting range 0x88 to 0xE7 in existing entries
    all_entries = {}
    all_entries.update(existing_entries)
    all_entries.update(katakana_entries)
    
    sorted_bytes = sorted(all_entries.keys())
    
    # 6. Write back to glyph_unicode.csv
    with open(unicode_path, 'w', encoding='utf-8') as f:
        f.write("text_byte_hex,vram_tile_hex,unicode_hex,character,rom_offset,category,mapping_source\n")
        for b in sorted_bytes:
            e = all_entries[b]
            f.write(f"{e['text_byte_hex']},{e['vram_tile_hex']},{e['unicode_hex']},{e['character']},{e['rom_offset']},{e['category']},{e['mapping_source']}\n")
            
    print(f"Successfully wrote {len(sorted_bytes)} entries to {unicode_path}")

if __name__ == '__main__':
    main()
