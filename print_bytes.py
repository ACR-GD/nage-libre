import struct
with open('Nage Libre - Seijaku no Suishin (Japan).sfc', 'rb') as f:
    rom = bytearray(f.read())

print("Bytes around 0FD44E:")
print(' '.join(f'{b:02X}' for b in rom[0x0FD44A:0x0FD45A]))
