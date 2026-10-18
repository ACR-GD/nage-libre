#!/usr/bin/env python3
"""Désassembleur 65816 (suivi M/X) pour les routines texte du prologue Nage Libre."""
from pathlib import Path

ROM = Path(__file__).resolve().parent.parent / "Nage Libre - Seijaku no Suishin (Japan).sfc"
rom = ROM.read_bytes()


def lorom(bank, addr):
    return ((bank & 0x7F) * 0x8000) + (addr - 0x8000)


# opcode table : nom, mode
# modes: imp, imm_m(A width), imm_x(X width), imm8, abs, absx, absy, absl, abslx,
#        dp, dpx, dpy, dpind, dpindl, dpindy, dpindly, rel, rell, mv, acc, sr, sry
OPS = {
    0x00: ("BRK", "imm8"), 0x02: ("COP", "imm8"),
    0x08: ("PHP", "imp"), 0x0B: ("PHD", "imp"), 0x0C: ("TSB", "abs"),
    0x18: ("CLC", "imp"), 0x1B: ("TCS", "imp"),
    0x20: ("JSR", "abs"), 0x22: ("JSL", "absl"), 0x28: ("PLP", "imp"),
    0x2B: ("PLD", "imp"),
    0x38: ("SEC", "imp"), 0x3B: ("TSC", "imp"),
    0x40: ("RTI", "imp"), 0x48: ("PHA", "imp"), 0x4B: ("PHK", "imp"),
    0x4C: ("JMP", "abs"), 0x5A: ("PHY", "imp"), 0x5B: ("TCD", "imp"),
    0x5C: ("JML", "absl"),
    0x60: ("RTS", "imp"), 0x62: ("PER", "rell"), 0x68: ("PLA", "imp"),
    0x6B: ("RTL", "imp"), 0x6C: ("JMP", "absind"),
    0x78: ("SEI", "imp"), 0x7A: ("PLY", "imp"),
    0x80: ("BRA", "rel"), 0x82: ("BRL", "rell"), 0x88: ("DEY", "imp"),
    0x8B: ("PHB", "imp"), 0x98: ("TYA", "imp"), 0x9A: ("TXS", "imp"),
    0x9B: ("TXY", "imp"),
    0xA8: ("TAY", "imp"), 0xAA: ("TAX", "imp"), 0xAB: ("PLB", "imp"),
    0xB8: ("CLV", "imp"), 0xBA: ("TSX", "imp"), 0xBB: ("TYX", "imp"),
    0xC8: ("INY", "imp"), 0xCA: ("DEX", "imp"), 0xCB: ("WAI", "imp"),
    0xD8: ("CLD", "imp"), 0xDA: ("PHX", "imp"), 0xDB: ("STP", "imp"),
    0xE8: ("INX", "imp"), 0xEA: ("NOP", "imp"), 0xEB: ("XBA", "imp"),
    0xF8: ("SED", "imp"), 0xFA: ("PLX", "imp"), 0xFB: ("XCE", "imp"),
    0x1A: ("INC", "acc"), 0x3A: ("DEC", "acc"),
    0xC2: ("REP", "imm8"), 0xE2: ("SEP", "imm8"),
}

# familles régulières (low nibble pattern) — on gère les principales
def base_op(b):
    if b in OPS:
        return OPS[b]
    hi = b & 0xF0
    lo = b & 0x0F
    # exceptions colonne 2 et autres : priorité sur le motif de groupe
    misc0 = {
        0xA2:("LDX","imm_x"),0xA0:("LDY","imm_x"),
        0xE0:("CPX","imm_x"),0xC0:("CPY","imm_x"),
    }
    if b in misc0:
        return misc0[b]
    name = {0x00:"ORA",0x20:"AND",0x40:"EOR",0x60:"ADC",0x80:"STA",
            0xA0:"LDA",0xC0:"CMP",0xE0:"SBC"}.get(hi)
    if name and lo in (0x1,0x3,0x5,0x7,0x9,0xD,0xF):
        # addressing by low nibble (group 1) — PAS la colonne 2
        mode = {0x1:"dpindx",0x3:"sr",0x5:"dp",0x7:"dpindl",
                0x9:"imm_m",0xD:"abs",0xF:"absl"}[lo]
        return (name, mode)
    if name and lo in (0xB,) and hi in (0x00,0x20,0x40,0x60,0x80,0xA0,0xC0,0xE0):
        pass
    # group with ,Y / ,X
    name2 = {0x10:"ORA",0x30:"AND",0x50:"EOR",0x70:"ADC",0x90:"STA",
             0xB0:"LDA",0xD0:"CMP",0xF0:"SBC"}.get(hi)
    if name2 and lo in (0x1,0x2,0x5,0x7,0x9,0xD,0xF):
        mode={0x1:"dpindy",0x2:"dpind",0x5:"dpx",0x7:"dpindly",
              0x9:"absy",0xD:"absx",0xF:"abslx"}[lo]
        return (name2,mode)
    # branches
    br={0x10:"BPL",0x30:"BMI",0x50:"BVC",0x70:"BVS",0x90:"BCC",
        0xB0:"BCS",0xD0:"BNE",0xF0:"BEQ"}
    if b in br: return (br[b],"rel")
    # LDX/LDY/STX/STY/CPX/CPY/INC/DEC/etc subset
    misc={
        0xA2:("LDX","imm_x"),0xA0:("LDY","imm_x"),
        0xA6:("LDX","dp"),0xA4:("LDY","dp"),0xAE:("LDX","abs"),0xAC:("LDY","abs"),
        0xB6:("LDX","dpy"),0xB4:("LDY","dpx"),0xBE:("LDX","absy"),0xBC:("LDY","absx"),
        0x86:("STX","dp"),0x84:("STY","dp"),0x8E:("STX","abs"),0x8C:("STY","abs"),
        0x96:("STX","dpy"),0x94:("STY","dpx"),
        0xE0:("CPX","imm_x"),0xC0:("CPY","imm_x"),
        0xE4:("CPX","dp"),0xC4:("CPY","dp"),0xEC:("CPX","abs"),0xCC:("CPY","abs"),
        0xE6:("INC","dp"),0xC6:("DEC","dp"),0xEE:("INC","abs"),0xCE:("DEC","abs"),
        0xF6:("INC","dpx"),0xD6:("DEC","dpx"),0xFE:("INC","absx"),0xDE:("DEC","absx"),
        0x06:("ASL","dp"),0x0A:("ASL","acc"),0x0E:("ASL","abs"),0x16:("ASL","dpx"),0x1E:("ASL","absx"),
        0x46:("LSR","dp"),0x4A:("LSR","acc"),0x4E:("LSR","abs"),0x56:("LSR","dpx"),0x5E:("LSR","absx"),
        0x26:("ROL","dp"),0x2A:("ROL","acc"),0x2E:("ROL","abs"),
        0x66:("ROR","dp"),0x6A:("ROR","acc"),0x6E:("ROR","abs"),
        0x24:("BIT","dp"),0x2C:("BIT","abs"),0x89:("BIT","imm_m"),
        0x64:("STZ","dp"),0x74:("STZ","dpx"),0x9C:("STZ","abs"),0x9E:("STZ","absx"),
        0x54:("MVN","mv"),0x44:("MVP","mv"),
        0xF4:("PEA","abs"),0xD4:("PEI","dp"),
        0xDC:("JML","absind"),0x7C:("JMP","absindx"),0xFC:("JSR","absindx"),
    }
    if b in misc: return misc[b]
    return ("?%02X"%b,"imp")


SIZES = {"imp":1,"acc":1,"imm8":2,"abs":3,"absl":4,"dp":2,"dpx":2,"dpy":2,
         "dpind":2,"dpindl":2,"dpindx":2,"dpindy":2,"dpindly":2,"sr":2,"sry":2,
         "rel":2,"rell":3,"mv":3,"absx":3,"absy":3,"abslx":4,"absind":3,"absindx":3,"absindl":4}


def disasm(bank, addr, n=60, mflag=0, xflag=0):
    off = lorom(bank, addr)
    pc = addr
    out = []
    for _ in range(n):
        b = rom[off]
        name, mode = base_op(b)
        if mode == "imm_m":
            sz = 3 if mflag == 0 else 2
        elif mode == "imm_x":
            sz = 3 if xflag == 0 else 2
        else:
            sz = SIZES.get(mode, 1)
        operand = rom[off+1:off+sz]
        snes = (bank << 16) | pc
        txt = fmt(name, mode, operand, snes, sz)
        out.append(f"  ${snes:06X}: {' '.join(f'{rom[off+k]:02X}' for k in range(sz)):<12} {txt}")
        if b == 0xC2:  # REP
            if operand[0] & 0x20: mflag = 0
            if operand[0] & 0x10: xflag = 0
        elif b == 0xE2:  # SEP
            if operand[0] & 0x20: mflag = 1
            if operand[0] & 0x10: xflag = 1
        if name in ("RTS","RTL","RTI","JMP","JML","BRA","BRL","STP"):
            out.append("  ---")
            break
        off += sz; pc += sz
    return out


def fmt(name, mode, op, snes, sz):
    def w(): return op[0] | (op[1]<<8) if len(op)>=2 else (op[0] if op else 0)
    if mode == "imp": return name
    if mode == "acc": return f"{name} A"
    if mode == "imm8": return f"{name} #${op[0]:02X}"
    if mode == "imm_m" or mode=="imm_x":
        v = w() if sz==3 else op[0]
        return f"{name} #${v:0{(sz-1)*2}X}"
    if mode == "abs": return f"{name} ${w():04X}"
    if mode == "absx": return f"{name} ${w():04X},X"
    if mode == "absy": return f"{name} ${w():04X},Y"
    if mode == "absl": return f"{name} ${op[2]:02X}{op[1]:02X}{op[0]:02X}"
    if mode == "abslx": return f"{name} ${op[2]:02X}{op[1]:02X}{op[0]:02X},X"
    if mode == "dp": return f"{name} ${op[0]:02X}"
    if mode == "dpx": return f"{name} ${op[0]:02X},X"
    if mode == "dpy": return f"{name} ${op[0]:02X},Y"
    if mode == "dpind": return f"{name} (${op[0]:02X})"
    if mode == "dpindl": return f"{name} [${op[0]:02X}]"
    if mode == "dpindx": return f"{name} (${op[0]:02X},X)"
    if mode == "dpindy": return f"{name} (${op[0]:02X}),Y"
    if mode == "dpindly": return f"{name} [${op[0]:02X}],Y"
    if mode == "sr": return f"{name} ${op[0]:02X},S"
    if mode == "rel":
        d = op[0] if op[0]<128 else op[0]-256
        return f"{name} ${(snes & 0xFFFF)+2+d & 0xFFFF:04X}"
    if mode == "rell":
        d = w(); d = d if d<32768 else d-65536
        return f"{name} ${(snes & 0xFFFF)+3+d & 0xFFFF:04X}"
    if mode == "mv": return f"{name} ${op[0]:02X},${op[1]:02X}"
    if mode == "absind": return f"{name} (${w():04X})"
    if mode == "absindx": return f"{name} (${w():04X},X)"
    return name


def opcode_table():
    """Extrait la table d'opcodes de l'interpr\u00e9teur de script $83:8103 et classe
    chaque handler (texte / pointeur / d\u00e9compression)."""
    start = lorom(0x83, 0x8103)
    table = {}
    i = start
    while i < lorom(0x83, 0x83E2):
        if rom[i] == 0xC9 and rom[i+2] == 0x00 and rom[i+3] == 0xD0 and rom[i+5] == 0x20:
            opc = rom[i+1]
            tgt = rom[i+6] | (rom[i+7] << 8)
            table[opc] = tgt
            i += 11
        else:
            i += 1
    print("opc  handler    fonction")
    for k in sorted(table):
        o = lorom(0x83, table[k]); blob = rom[o:o+400]
        feats = []
        if b"\x22\xCA\xF4\x80" in blob: feats.append("texte(F4CA)")
        if b"\x22\xA7\xF4\x80" in blob: feats.append("texte(F4A7)")
        if b"\x69\xC0\x64" in blob: feats.append("ptr+64C0")
        if b"\x22\x63\xFA\x80" in blob: feats.append("decomp(FA63)")
        print(f"{k:02X}   $83:{table[k]:04X}    {', '.join(feats) if feats else '(contr\u00f4le)'}")
    return table


if __name__ == "__main__":
    import sys
    if len(sys.argv) >= 2 and sys.argv[1] == "opcodes":
        opcode_table()
        sys.exit()
    routines = [
        ("D70C boucle acte", 0x87, 0xD70C, 80),
        ("D9D7 gfx/init", 0x87, 0xD9D7, 40),
        ("DA3B ligne 1", 0x87, 0xDA3B, 40),
        ("DA8C ligne 2", 0x87, 0xDA8C, 40),
        ("D990 -> F4A7", 0x87, 0xD990, 30),
        ("F4A7 dispatch", 0x80, 0xF4A7, 12),
        ("F4AB typewriter", 0x80, 0xF4AB, 80),
    ]
    if len(sys.argv) >= 3:
        bank = int(sys.argv[1], 16); addr = int(sys.argv[2], 16)
        n = int(sys.argv[3]) if len(sys.argv) > 3 else 60
        for l in disasm(bank, addr, n): print(l)
    else:
        for label, bank, addr, n in routines:
            print(f"\n===== {label}  (${bank:02X}:{addr:04X}) =====")
            for l in disasm(bank, addr, n): print(l)
