import os

def snes_lorom_to_offset(bank, addr):
    """
    Translates a SNES LoROM bank:address to a physical ROM file offset.
    """
    if bank < 0x80:
        bank += 0x80
    if addr < 0x8000:
        return None
    return ((bank - 0x80) * 0x8000) + (addr - 0x8000)

def load_tbl(tbl_path):
    """
    Loads a standard .tbl mapping file (HEX=Char).
    """
    table = {}
    if not os.path.exists(tbl_path):
        print(f"Table file {tbl_path} not found.")
        return table
    
    with open(tbl_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or "=" not in line:
                continue
            h, c = line.split("=", 1)
            try:
                val = int(h, 16)
                table[val] = c
            except ValueError:
                continue
    return table

def decode_string(raw, table):
    """
    Decodes raw bytes using the custom table format.
    """
    decoded = []
    i = 0
    while i < len(raw):
        b = raw[i]
        
        # 0xFF xx terminator
        if b == 0xFF and i + 1 < len(raw):
            sub = raw[i + 1]
            decoded.append(f"[FF{sub:02X}]")
            i += 2
            break
            
        # 0xFE terminator
        if b == 0xFE:
            decoded.append("[FE]")
            i += 1
            break
            
        # 0x00 terminator
        if b == 0x00:
            break
            
        # Control codes
        if b == 0x01:
            decoded.append("[01]")
            i += 1
            continue
            
        if b == 0x02:
            decoded.append("…")
            i += 1
            continue
            
        # Direct glyph 8D xx
        if b == 0x8D and i + 1 < len(raw):
            glyph_id = raw[i + 1]
            char = table.get(glyph_id, f"{{{glyph_id:02X}}}")
            decoded.append(char)
            i += 2
            continue
            
        # 3-byte sequence 20 xx yy
        if b == 0x20 and i + 2 < len(raw):
            glyph_id = raw[i + 1]
            char = table.get(glyph_id, f"{{{glyph_id:02X}}}")
            decoded.append(char)
            i += 3
            continue
            
        # Default glyph mapping
        char = table.get(b, f"{{{b:02X}}}")
        decoded.append(char)
        i += 1
        
    return "".join(decoded)

def is_japanese_dialogue_char(c):
    if not c or len(c) != 1:
        return False
    code = ord(c)
    # Hiragana range: 0x3040-0x309F
    if 0x3040 <= code <= 0x309F:
        return True
    # Katakana range: 0x30A0-0x30FF
    if 0x30A0 <= code <= 0x30FF:
        return True
    # Kanji
    if c in ("事", "見", "言", "思"):
        return True
    # Punctuation / Fullwidth punctuation
    if c in ("？", "！", "・", "、", "。", "「", "」", "ー", "゛", "゜"):
        return True
    return False

def analyze_candidate(raw, table):
    i = 0
    mapped_count = 0
    unmapped_count = 0
    control_count = 0
    
    while i < len(raw):
        b = raw[i]
        
        # Terminators
        if b == 0xFF and i + 1 < len(raw):
            control_count += 1
            i += 2
            break
        if b == 0xFE:
            control_count += 1
            i += 1
            break
        if b == 0x00:
            break
            
        # Control codes
        if b == 0x01:
            control_count += 1
            i += 1
            continue
        if b == 0x02:
            mapped_count += 1  # "…" is mapped
            i += 1
            continue
            
        # Direct glyph 8D xx
        if b == 0x8D and i + 1 < len(raw):
            glyph_id = raw[i + 1]
            char = table.get(glyph_id)
            if char and is_japanese_dialogue_char(char):
                mapped_count += 1
            else:
                unmapped_count += 1
            i += 2
            continue
            
        # 3-byte sequence 20 xx yy
        if b == 0x20 and i + 2 < len(raw):
            glyph_id = raw[i + 1]
            char = table.get(glyph_id)
            if char and is_japanese_dialogue_char(char):
                mapped_count += 1
            else:
                unmapped_count += 1
            i += 3
            continue
            
        # Default glyph mapping
        char = table.get(b)
        if char:
            if is_japanese_dialogue_char(char):
                mapped_count += 1
            else:
                control_count += 1
        else:
            unmapped_count += 1
        i += 1
        
    return mapped_count, unmapped_count, control_count

def has_consecutive_repeats(text, max_repeat=3):
    count = 1
    last_char = None
    for char in text:
        if char == last_char and char not in ("…", "ー", "。", "、", "！", "？", " ", "[", "]", "{", "}"):
            count += 1
            if count >= max_repeat:
                return True
        else:
            count = 1
            last_char = char
    return False

def score_text_v2(raw, table):
    """
    Refined scoring function to filter out bytecode, script data, and tables.
    """
    if len(raw) < 2:
        return False
        
    # Check if there is 0x00 inside the string body (before the terminator)
    body_len = len(raw)
    for idx, b in enumerate(raw):
        if b == 0xFE:
            body_len = idx
            break
        if b == 0xFF and idx + 1 < len(raw):
            body_len = idx
            break
        if b == 0x00:
            body_len = idx
            break
            
    body = raw[:body_len]
    if 0x00 in body:
        return False
        
    mapped_count, unmapped_count, control_count = analyze_candidate(raw, table)
    
    # We need a minimum of mapped characters
    if mapped_count < 3:
        return False
        
    # Unmapped ratio check: too many unmapped bytes means it's probably code/data
    total_content = mapped_count + unmapped_count
    if total_content > 0:
        unmapped_ratio = unmapped_count / total_content
        if unmapped_ratio > 0.25: # Max 25% unmapped bytes
            return False
            
    # Check for consecutive repeats (e.g. くくく)
    decoded_body = decode_string(body, table)
    if has_consecutive_repeats(decoded_body):
        return False
        
    return True

def main():
    workspace = "/Users/acr/Develop/nage-libre"
    rom_path = os.path.join(workspace, "Nage Libre - Seijaku no Suishin (Japan).sfc")
    tbl_path = os.path.join(workspace, "nage_libre.tbl")
    out_path = os.path.join(workspace, "docs", "decoded_dialogues.txt")
    
    if not os.path.exists(rom_path):
        print(f"ROM not found at {rom_path}")
        return
        
    with open(rom_path, "rb") as f:
        rom_data = f.read()
        
    table = load_tbl(tbl_path)
    
    results = {}  # offset -> (decoded_text, raw_bytes, source)
    
    # 1. Scan Dialogue Regions for FF-terminated strings
    # Regions: (0x22000, 0x38000), (0x38000, 0x48000), (0x20000, 0x22000)
    ff_terminators = (0x05, 0x10, 0x01, 0x02, 0x09, 0x0A)
    regions = [
        (0x22000, 0x38000, "bank84_dialogue"),
        (0x38000, 0x48000, "dialogue_extended"),
        (0x20000, 0x22000, "bank84_early")
    ]
    
    for start, end, reg_name in regions:
        # FF terminated
        for i in range(start, end - 1):
            if rom_data[i] == 0xFF and rom_data[i+1] in ff_terminators:
                # Found a terminator. Walk back to find the start of the string.
                s = i - 1
                while s > start and rom_data[s] != 0xFF:
                    s -= 1
                s += 1
                
                # Strip leading double zeros padding
                while s + 1 < i and rom_data[s] == 0 and rom_data[s+1] == 0:
                    s += 2
                    
                raw = rom_data[s:i+2]
                if score_text_v2(raw, table):
                    text = decode_string(raw, table)
                    results[s] = (text, raw, f"{reg_name}_FF")
                    
        # FE terminated
        for i in range(start, end):
            if rom_data[i] == 0xFE:
                s = i - 1
                while s > start and rom_data[s] not in (0xFF, 0xFE, 0x00):
                    s -= 1
                s += 1
                raw = rom_data[s:i+1]
                if score_text_v2(raw, table):
                    text = decode_string(raw, table)
                    results[s] = (text, raw, f"{reg_name}_FE")
                    
        # 01 prefixed
        for i in range(start, end - 8):
            if rom_data[i] == 0x01:
                e = i + 1
                limit = min(i + 400, end)
                while e < limit:
                    if rom_data[e] == 0xFE or (rom_data[e] == 0xFF and e + 1 < end):
                        break
                    if rom_data[e] == 0 and e > i + 6:
                        break
                    e += 1
                raw = rom_data[i:e]
                if score_text_v2(raw, table):
                    text = decode_string(raw, table)
                    results[i] = (text, raw, f"{reg_name}_01_prefix")

    # 2. Extract from script pointers (follow 3-byte pointers in script region 0x20000-0x35000)
    targets = set()
    for pos in range(0x20000, 0x35000 - 3):
        bank = rom_data[pos + 2]
        if 0x84 <= bank <= 0x8F:
            addr = rom_data[pos] | (rom_data[pos + 1] << 8)
            offset = snes_lorom_to_offset(bank, addr)
            if offset is not None and 0 <= offset < len(rom_data):
                targets.add(offset)
                
    for offset in sorted(targets):
        if offset in results:
            continue
        limit = min(256, len(rom_data) - offset)
        raw_slice = rom_data[offset : offset + limit]
        
        # Find exact end
        end = limit
        for j in range(limit):
            if raw_slice[j] in (0xFE, 0xFF):
                end = j + (2 if raw_slice[j] == 0xFF and j + 1 < limit else 1)
                break
        raw = raw_slice[:end]
        if score_text_v2(raw, table):
            text = decode_string(raw, table)
            results[offset] = (text, raw, "script_pointer")

    # Prune substrings (if a string is strictly inside another nearby string, remove it)
    sorted_offsets = sorted(results.keys())
    to_keep = {off: True for off in sorted_offsets}
    
    for i, off1 in enumerate(sorted_offsets):
        for j, off2 in enumerate(sorted_offsets):
            if off1 == off2 or not to_keep[off1]:
                continue
            text1, raw1, _ = results[off1]
            text2, raw2, _ = results[off2]
            
            # Check if range 1 is inside range 2 and distance is small
            if off1 >= off2 and off1 + len(raw1) <= off2 + len(raw2) and len(raw1) < len(raw2) and abs(off1 - off2) < 8:
                to_keep[off1] = False

    # Write output to file
    print(f"Writing decoded dialogue text to {out_path}...")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("ROM Offset | Source | Hex Bytes | Decoded Text\n")
        f.write("-" * 80 + "\n")
        for off in sorted_offsets:
            if to_keep[off]:
                text, raw, src = results[off]
                hex_str = " ".join(f"{b:02X}" for b in raw)
                f.write(f"0x{off:06X} | {src:<20} | {hex_str} | {text}\n")
                
    print(f"Successfully decoded {sum(to_keep.values())} strings.")

if __name__ == "__main__":
    main()
