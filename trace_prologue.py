import struct

with open('Nage Libre - Seijaku no Suishin (Japan).sfc', 'rb') as f:
    rom = bytearray(f.read())

def lorom(bank, addr):
    return (bank & 0x7F) * 0x8000 + (addr - 0x8000)

def get_word(bank, addr):
    off = lorom(bank, addr)
    return struct.unpack_from('<H', rom, off)[0]

def get_byte(bank, addr):
    off = lorom(bank, addr)
    return rom[off]

def disassemble_block(bank, start_addr, num_bytes):
    print(f"\nDisassembly of ${bank:02X}:{start_addr:04X}:")
    off = lorom(bank, start_addr)
    for i in range(0, num_bytes, 16):
        hx = ' '.join(f'{b:02X}' for b in rom[off+i:off+i+16])
        print(f"  ${bank:02X}:{start_addr+i:04X}: {hx}")

# Let's trace from $80:938C
disassemble_block(0x80, 0x938C, 64)

# We know $80:9393 JSL $87:D63B
disassemble_block(0x87, 0xD63B, 128)

print("\nWait, let's look at $87:D66F (JSR $DA0E) and $87:D67E (JSR $D8CF)")
# DA0E was the table loader
disassemble_block(0x87, 0xDA0E, 64)

print("\nWhat does $87:DA3B do?")
disassemble_block(0x87, 0xDA3B, 64)
