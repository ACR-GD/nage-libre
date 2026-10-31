#!/usr/bin/env python3
"""
Écran de sauvegarde/chargement : « 2面 » -> « St2 ».

La routine $87:E8AE (une copie par fichier : $87:E8AE / $87:E911 / $87:E974)
place le curseur en $15, lit l'étape atteinte du fichier, puis :
    0      -> « なし » ($87:89EB, déjà traduit « None »)
    $18    -> « EX »   ($87:8AE5)
    sinon  -> nombre sur 2 chiffres ($80:F6E8, X=2) puis « 面 » ($87:89C1)
Le chiffre est une tuile paire (« 2» = blanc+2) et 面 une tuile 16x16 : il ne
reste que 2 tuiles, et « St » devant le nombre donnerait « St 2 ».

On remplace, dans chaque copie, la séquence nombre + 面 (29 octets à partir du
LDX #$0002) par un JSL vers une petite routine en $BF:FC00 qui affiche une
chaîne demi-chasse précomposée « St1 » .. « St23 » (4 caractères, complétée
d'une espace = largeur exacte de « None » / « 2面 », pas de rémanence).

apply(rom) est appelé par build_full_translation.py (après BT.apply).
"""
import struct

from build_scene_injection import encode_hw

CODE_FILE = 0x1FFC00            # $BF:FC00
CODE_SNES = 0xBFFC00
AREA_END = 0x1FFE00
MAX_STAGE = 23                  # $18 = EX, géré par le jeu
WIDTH = 4                       # demi-chasses : « None » = 2 tuiles paires

SITES = [0x87E8C4, 0x87E927, 0x87E98A]   # LDX #$0002 de chaque copie
ORIG = bytes.fromhex("a20200" "22e8f680" "e220" "48" "a9c18509" "a9898" "50a" "a987850b"
                     "68" "c220" "22a7f480")


def _file(snes):
    return ((snes >> 16) & 0x7F) * 0x8000 + (snes & 0x7FFF)


def apply(rom):
    strings = bytearray()
    for n in range(1, MAX_STAGE + 1):
        ids = encode_hw(f"St{n}".ljust(WIDTH)) + [0xFFFF]
        strings += b"".join(struct.pack("<H", i) for i in ids)
    rec = 2 * (WIDTH + 1)                                   # 10 octets par chaîne

    table = CODE_SNES + 0x40
    base = (table & 0xFFFF) - rec                           # étape 1 = première chaîne
    code = bytes([
        0x0A,                       # ASL A          ; 2n
        0x48,                       # PHA
        0x0A, 0x0A,                 # ASL A x2       ; 8n
        0x18, 0x63, 0x01,           # CLC / ADC 1,S  ; 10n
        0xFA,                       # PLX            ; (jette 2n)
        0x18, 0x69, base & 0xFF, base >> 8,   # CLC / ADC #base
        0xE2, 0x20,                 # SEP #$20
        0x85, 0x09,                 # STA $09
        0xEB,                       # XBA
        0x85, 0x0A,                 # STA $0A
        0xA9, table >> 16,          # LDA #$BF
        0x85, 0x0B,                 # STA $0B
        0xC2, 0x20,                 # REP #$20
        0x22, 0xA7, 0xF4, 0x80,     # JSL $80:F4A7
        0x6B,                       # RTL
    ])
    assert len(code) <= 0x40 and rec == 10
    blob = code.ljust(0x40, b"\xFF") + strings
    if CODE_FILE + len(blob) > AREA_END:
        raise SystemExit("build_save_menu : zone $BF:FC00 trop petite")
    if any(b not in (0x00, 0xFF) for b in rom[CODE_FILE:CODE_FILE + len(blob)]):
        raise SystemExit("build_save_menu : $BF:FC00 déjà utilisé")
    rom[CODE_FILE:CODE_FILE + len(blob)] = blob

    for s in SITES:
        o = _file(s)
        if bytes(rom[o:o + len(ORIG)]) != ORIG:
            raise SystemExit(f"build_save_menu : code inattendu en ${s >> 16:02X}:{s & 0xFFFF:04X}")
        patch = bytes([0x22, CODE_SNES & 0xFF, (CODE_SNES >> 8) & 0xFF, CODE_SNES >> 16])
        rom[o:o + len(ORIG)] = patch + b"\xEA" * (len(ORIG) - len(patch))
    return MAX_STAGE
