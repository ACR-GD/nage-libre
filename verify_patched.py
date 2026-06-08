with open('Nage Libre - Patched.sfc', 'rb') as f:
    rom = f.read()

def dump_hex(offset, size):
    hx = ' '.join(f'{b:02X}' for b in rom[offset:offset+size])
    print(f"Offset {offset:06X}: {hx}")

dump_hex(0x0389C5, 24)
dump_hex(0x038A51, 14)
dump_hex(0x038A61, 14)
dump_hex(0x038A71, 10)
