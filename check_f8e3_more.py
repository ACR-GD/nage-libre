with open('Nage Libre - Seijaku no Suishin (Japan).sfc', 'rb') as f:
    rom = bytearray(f.read())
def lorom(bank, addr): return (bank & 0x7F) * 0x8000 + (addr - 0x8000)
off = lorom(0x83, 0xF8E3)
count = 0
for b in rom[off:]:
    if b == 0xFF: count += 1
    else: break
print(f"Consecutive FF bytes: {count}")
