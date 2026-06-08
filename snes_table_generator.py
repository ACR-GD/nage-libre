import os

def main():
    workspace = "/Users/acr/Develop/nage-libre"
    csv_path = os.path.join(workspace, "docs", "glyph_unicode.csv")
    tbl_path = os.path.join(workspace, "nage_libre.tbl")

    # Start with standard control codes
    mappings = {
        0x01: "[01]",
        0x02: "…",
        0xFE: "[FE]",
    }

    # Load existing mappings from CSV (preserving Hiragana)
    if os.path.exists(csv_path):
        print(f"Reading existing mappings from {csv_path}...")
        with open(csv_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        
        for line in lines[1:]:
            line = line.strip()
            if not line:
                continue
            parts = line.split(",")
            if len(parts) >= 4:
                byte_hex = parts[0].strip()
                character = parts[3].strip()
                
                try:
                    val = int(byte_hex, 16)
                    # Preserve Hiragana and other known system symbols, but skip the incorrect Katakana (0x88 to 0xE7)
                    if 0x08 <= val <= 0x67 or (val < 0x88 or val > 0xE7):
                        if character and character != "〓":
                            mappings[val] = character
                except ValueError:
                    continue

    # Initialize Katakana dialogue range (0x88 to 0xE7) as placeholders for now
    for val in range(0x88, 0xE8):
        if val not in mappings:
            mappings[val] = f"{{{val:02X}}}"

    # Write to standard .tbl file (HEX=Char)
    print(f"Writing table file to {tbl_path}...")
    with open(tbl_path, "w", encoding="utf-8") as f:
        # Sort by byte value
        for val in sorted(mappings.keys()):
            char = mappings[val]
            f.write(f"{val:02X}={char}\n")

    print("Done! Table file generated successfully.")

if __name__ == "__main__":
    main()
