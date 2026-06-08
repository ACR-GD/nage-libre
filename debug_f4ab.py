import struct
with open('Nage Libre - Patched.sfc', 'rb') as f:
    rom = bytearray(f.read())

def lorom(bank, addr):
    return (bank & 0x7F) * 0x8000 + (addr - 0x8000)

# We want to hook $80:F4AB.
# $80:F4AB: 08 C2 30 48  (PHP; REP #$30; PHA)
# We can overwrite it with JSL $83:FA80
# $83:FA80:
# PHP; REP #$30; PHA
# LDA $0B; STA $7FFF00 ; Bank
# LDA $09; STA $7FFF02 ; Addr
# JSL $80:88E4 (the original instruction at F4AF)
# RTL

hook = bytearray([
    0x08,             # PHP
    0xC2, 0x30,       # REP #$30
    0x48,             # PHA
    0xA5, 0x0B,       # LDA $0B
    0x8F, 0x00, 0xFF, 0x7F, # STA $7FFF00
    0xA5, 0x09,       # LDA $09
    0x8F, 0x02, 0xFF, 0x7F, # STA $7FFF02
    0x22, 0xE4, 0x88, 0x80, # JSL $80:88E4
    0x6B              # RTL
])

# Write hook to $83:FA80 (ROM 0x1FA80)
rom[0x01FA80:0x01FA80+len(hook)] = hook

# Patch $80:F4AB
# 22 80 FA 83 EA
# JSL $83:FA80; NOP
patch_addr = lorom(0x80, 0xF4AB)
rom[patch_addr:patch_addr+5] = bytes([0x22, 0x80, 0xFA, 0x83, 0xEA])

# Wait, F4AB originally has:
# 08 C2 30 48 22 E4 88 80  (8 bytes)
# We replaced the first 5 bytes. The remaining 3 are 88 80 and what?
# Oh, the original code is:
# F4AB: 08 C2 30 48
# F4AF: 22 E4 88 80
# We replace 08 C2 30 48 22 with JSL $83:FA80 (which is 4 bytes).
# Wait, JSL is 4 bytes: 22 addr_lo addr_hi bank.
# So we overwrite 4 bytes. We can't overwrite 4 bytes and leave the 5th byte dangling if it's part of an instruction.
# Let's overwrite exactly 4 bytes: 08 C2 30 48.
# And our hook does 08 C2 30 48 before returning.

hook = bytearray([
    0x08,             # PHP
    0xC2, 0x30,       # REP #$30
    0x48,             # PHA
    0xA5, 0x0B,       # LDA $0B
    0x8F, 0x00, 0xFF, 0x7F, # STA $7FFF00
    0xA5, 0x09,       # LDA $09
    0x8F, 0x02, 0xFF, 0x7F, # STA $7FFF02
    0x6B              # RTL
])
rom[0x01FA80:0x01FA80+len(hook)] = hook
rom[patch_addr:patch_addr+4] = bytes([0x22, 0x80, 0xFA, 0x83])

with open('Nage Libre - Debug.sfc', 'wb') as f:
    f.write(rom)

print("Created Nage Libre - Debug.sfc with F4AB pointer dumper.")
