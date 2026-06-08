import subprocess
import os

with open('debug_bin.bin', 'wb') as f:
    f.write(bytes.fromhex("08 C2 30 48 DA 5A AE 40 02 20 90 F3 A0 02 00 B0 03 A0 01 00 18 6D 48 07 9D 12 08 98 9D 14 08 AD 41 11 29 00 FF 4A 4A 4A E2 20 18 6D 41 11 C2 20 9D 16 08 E2 20 AD 41 11 18 7D 14 08 CD 44 11 30"))

print("Disassembled F433:")
# We can just write out the manual disassembly since we know most of these bytes
# 08 PHP
# C2 30 REP #$30
# 48 PHA
# DA PHX
# 5A PHY
# AE 40 02 LDX $0240
# 20 90 F3 JSR $F390  (loads font graphic)
# A0 02 00 LDY #$0002
# B0 03    BCS +3
# A0 01 00 LDY #$0001
# 18       CLC
# 6D 48 07 ADC $0748
# 9D 12 08 STA $0812,X
# 98       TYA
# 9D 14 08 STA $0814,X
# AD 41 11 LDA $1141
# 29 00 FF AND #$FF00
# 4A 4A 4A LSR LSR LSR
# E2 20    SEP #$20
# 18       CLC
# 6D 41 11 ADC $1141
# C2 20    REP #$20
# 9D 16 08 STA $0816,X
# E2 20    SEP #$20
# AD 41 11 LDA $1141
# 18       CLC
# 7D 14 08 ADC $0814,X
# CD 44 11 CMP $1144
# 30       BMI ...
