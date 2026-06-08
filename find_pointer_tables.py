with open('/Users/acr/Develop/nage-libre/Nage Libre - Seijaku no Suishin (Japan).sfc', 'rb') as f:
    rom = f.read()

for bank in range(0x80, 0xC0):
    for offset in range(3):
        consecutive = 0
        start_idx = 0
        for i in range(offset + 2, len(rom), 3):
            if rom[i] == bank:
                if consecutive == 0:
                    start_idx = i - 2
                consecutive += 1
            else:
                if consecutive >= 50:
                    print(f"Found pointer table to Bank {bank:02X} at 0x{start_idx:06X}, {consecutive} pointers")
                consecutive = 0
