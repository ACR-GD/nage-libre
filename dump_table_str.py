from build_patched_rom import ROM_PATH, parse_text_table
with open(ROM_PATH, 'rb') as f: rom = bytearray(f.read())
orig = parse_text_table(rom)
for s in orig:
    if len(s['ids']) > 5:
        print(f"Line {s['line']}: {s['ids'][:5]}")
