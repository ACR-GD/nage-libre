import os

def hira_to_kata_char(c):
    if len(c) != 1:
        return c
    code = ord(c)
    if 0x3041 <= code <= 0x3096:
        return chr(code + 0x60)
    if c == "ゔ":
        return "ヴ"
    return c

def main():
    workspace = "/Users/acr/Develop/nage-libre"
    tbl_path = os.path.join(workspace, "nage_libre.tbl")

    if not os.path.exists(tbl_path):
        print("Table file not found.")
        return

    # Load existing table
    mappings = {}
    with open(tbl_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or "=" not in line:
                continue
            h, c = line.split("=", 1)
            try:
                val = int(h, 16)
                mappings[val] = c
            except ValueError:
                continue

    # Fill Katakana range 0x88 to 0xE7 based on Hiragana range 0x08 to 0x67
    for i in range(96):
        hira_val = 0x08 + i
        kata_val = 0x88 + i
        
        if hira_val in mappings:
            hira_char = mappings[hira_val]
            # Convert to Katakana
            kata_char = hira_to_kata_char(hira_char)
            mappings[kata_val] = kata_char
            print(f"Mapped 0x{kata_val:02X} -> {kata_char} (from 0x{hira_val:02X} -> {hira_char})")

    # Save the updated table back to nage_libre.tbl
    with open(tbl_path, "w", encoding="utf-8") as f:
        for val in sorted(mappings.keys()):
            f.write(f"{val:02X}={mappings[val]}\n")

    print("Table nage_libre.tbl updated successfully!")

if __name__ == "__main__":
    main()
