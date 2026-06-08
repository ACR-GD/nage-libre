import struct
with open('Nage Libre - Seijaku no Suishin (Japan).sfc', 'rb') as f:
    rom = bytearray(f.read())
def lorom(bank, addr): return (bank & 0x7F) * 0x8000 + (addr - 0x8000)

def dis(bank, addr, length):
    import subprocess
    start = lorom(bank, addr)
    with open('tmp.bin', 'wb') as f:
        f.write(rom[start:start+length])
    print(f"--- {bank:02X}:{addr:04X} ---")
    # We don't have a built-in disassembler, just dump hex
    hx = ' '.join(f'{b:02X}' for b in rom[start:start+length])
    print(hx)

dis(0x87, 0xEEAA, 32)
dis(0x87, 0xEAD3, 32)
