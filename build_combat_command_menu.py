#!/usr/bin/env python3
"""
Traduction du MENU DE COMMANDE en combat (待機/攻撃/アイテム/交換/ポケベル/アニメ/
セーブ) de Nage Libre — par HOOK runtime (aucune édition de police permanente).

Contexte (voir docs/combat_menu_text.md) :
  - Le menu est dessiné par le moteur de texte commun banque $80 (enveloppe
    $80:F8D8 = `JSR $F8DC ; RTL`, appelée par `JSL $80F8D8`). Le moteur décode un
    flux de glyphes COMPRESSÉ et assemble les glyphes dans un buffer de police
    WRAM, EN ORDRE DE DESSIN : la tuile d'indice T est à $7E:2000 + (T-$80)*16.
  - Les 7 commandes occupent des indices de tuile STABLES (top/bottom) :
        待機=90-94/A0-A4  攻撃=B5-B9/C5-C9  アイテム=95-99/A5-A9
        交換=9A-9E/AA-AE  ポケベル=B0-B4/C0-C4  アニメ=D0-D4/E0-E4  セーブ=BA-BE/CA-CE
  - Ce buffer est ensuite DMA'd en VRAM (BG3, char base $A000). La tilemap BG3
    référence ces indices.

Stratégie : on détourne la SORTIE du renderer $80:F902 (`REP #$30 ; PLY ; PLX`,
juste avant `PLA ; PLP ; RTS`) en `JML $80:FA80`. AINSI tout appel à $F8DC est
intercepté (peu importe le chemin d'appel : enveloppe $F8D8 ou JSR direct), juste
après la (re)construction du buffer de police et avant le DMA→VRAM (NMI). Notre
code rejoue les instructions écrasées, puis — si la signature du menu est présente
dans le buffer de police — recopie nos bitmaps de LETTRES anglaises (embarqués en
ROM, banque $80) par-dessus les tuiles de glyphe des commandes (MVN ROM→WRAM).
Lettre dans la tuile du HAUT, tuile du bas vidée. Enfin il rejoue l'épilogue
original (PLY PLX PLA PLP RTS).

Limite : 5 tuiles (8px) par commande → 5 lettres max. `攻撃` rendu **FIGHT**
(ATTACK = 6 ne tient pas).

Usage : python3 build_combat_command_menu.py        # patche nl-full-en.sfc
        (ou importé : apply(rom) depuis build_full_translation.py)
"""
from pathlib import Path

from patch_prologue_v3 import FONT, _rows_to_2bpp, fix_checksum

ROOT = Path(__file__).parent
OUT = ROOT / "nl-full-en.sfc"

# --- Implantation ---
HOOK_FILE = 0x07A80           # offset fichier de $80:FA80 (zone libre ~1283 o de FF)
HOOK_SNES = 0xFA80            # adresse $80:FA80
FREE_END_FILE = 0x07F10       # fin de la zone libre (hook demi-chasse en $80:FF10)
# Point de détournement : SORTIE du renderer $80:F902 (`C2 30 7A FA` =
# REP #$30 ; PLY ; PLX). On écrase 4 octets par `JML $80:FA80`.
EXIT_FILE = 0x07902
EXIT_ORIG = bytes([0xC2, 0x30, 0x7A, 0xFA])      # REP #$30 ; PLY ; PLX
EXIT_NEW = bytes([0x5C, HOOK_SNES & 0xFF, (HOOK_SNES >> 8) & 0xFF, 0x80])  # JML $80:FA80
# Au cas où une build précédente aurait détourné l'enveloppe $80:F8D8 : on la
# restaure à l'origine.
WRAP_FILE = 0x078D8
WRAP_ORIG = bytes([0x20, 0xDC, 0xF8, 0x6B])      # JSR $F8DC ; RTL
WRAP_OLDHOOK = bytes([0x5C, HOOK_SNES & 0xFF, (HOOK_SNES >> 8) & 0xFF, 0x80])

# Buffer de police WRAM (banque $7E) : tuile T → 0x2000 + (T-0x80)*16
def dst_off(tile):
    return 0x2000 + (tile - 0x80) * 16

# Signatures (buffer de police, banque $7E) : présentes uniquement quand le menu
# de combat est rendu.  待 (tuile $90 → $7E:2100) mot@+4 == $3718 ;
# 攻 (tuile $B5 → $7E:2350) mot@+6 == $7E01.
SIG1_ADDR, SIG1_VAL = 0x2104, 0x3718
SIG2_ADDR, SIG2_VAL = 0x2356, 0x7E01

# (tuiles_haut, tuiles_bas, mot)  — mot ≤ 5 lettres
CMDS = [
    ([0x90, 0x91, 0x92, 0x93, 0x94], [0xA0, 0xA1, 0xA2, 0xA3, 0xA4], "WAIT"),
    ([0xB5, 0xB6, 0xB7, 0xB8, 0xB9], [0xC5, 0xC6, 0xC7, 0xC8, 0xC9], "FIGHT"),
    ([0x95, 0x96, 0x97, 0x98, 0x99], [0xA5, 0xA6, 0xA7, 0xA8, 0xA9], "ITEM"),
    ([0x9A, 0x9B, 0x9C, 0x9D, 0x9E], [0xAA, 0xAB, 0xAC, 0xAD, 0xAE], "SWAP"),
    ([0xB0, 0xB1, 0xB2, 0xB3, 0xB4], [0xC0, 0xC1, 0xC2, 0xC3, 0xC4], "PAGER"),
    ([0xD0, 0xD1, 0xD2, 0xD3, 0xD4], [0xE0, 0xE1, 0xE2, 0xE3, 0xE4], "ANIME"),
    ([0xBA, 0xBB, 0xBC, 0xBD, 0xBE], [0xCA, 0xCB, 0xCC, 0xCD, 0xCE], "SAVE"),
]

BLANK_TILE = bytes(16)
def letter_tile_data(c):
    return _rows_to_2bpp(FONT[c][0])   # demi-haut 8x8 de la lettre


def build_plan():
    """Retourne (tiles, copies) : tiles = liste de tuiles 16 o dédupliquées ;
    copies = liste de (tile_index, dst_off)."""
    tiles, idx_of = [], {}
    def ti(data):
        if data not in idx_of:
            idx_of[data] = len(tiles)
            tiles.append(data)
        return idx_of[data]
    blank_i = ti(BLANK_TILE)
    copies = []
    for tops, bots, word in CMDS:
        for i, t in enumerate(tops):
            if i < len(word):
                copies.append((ti(letter_tile_data(word[i])), dst_off(t)))
            else:
                copies.append((blank_i, dst_off(t)))
        for t in bots:
            copies.append((blank_i, dst_off(t)))
    return tiles, copies


def assemble(pager=None):
    """Assemble hook + données. Retourne les octets à écrire à HOOK_FILE.
    `pager` = build_pager_menu.hook_params() : branche « bloc PAGER » (si fourni)."""
    tiles, copies = build_plan()

    # Le code a une taille FIXE (LDX/LDY/LDA immédiats = 3 o, MVN = 3 o), donc on
    # peut calculer l'adresse des données avant de remplir les opérandes.
    def build_code(data_base):
        c = bytearray()
        # On arrive ici à la place de `REP #$30 ; PLY ; PLX` (instr. écrasées).
        c += bytes([0xC2, 0x30])                   # REP #$30  (rejoué)
        # A/X/Y seront restaurés depuis la pile à la fin → libres à clobber ici.
        c += bytes([0xAF, SIG1_ADDR & 0xFF, (SIG1_ADDR >> 8) & 0xFF, 0x7E])  # LDA $7E:SIG1
        c += bytes([0xC9, SIG1_VAL & 0xFF, (SIG1_VAL >> 8) & 0xFF])          # CMP #SIG1
        c += bytes([0xF0, 0x03])                   # BEQ +3
        j1 = len(c); c += bytes([0x4C, 0x00, 0x00])# JMP done
        c += bytes([0xAF, SIG2_ADDR & 0xFF, (SIG2_ADDR >> 8) & 0xFF, 0x7E])  # LDA $7E:SIG2
        c += bytes([0xC9, SIG2_VAL & 0xFF, (SIG2_VAL >> 8) & 0xFF])          # CMP #SIG2
        c += bytes([0xF0, 0x03])                   # BEQ +3
        j2 = len(c); c += bytes([0x4C, 0x00, 0x00])# JMP done
        c += bytes([0x8B])                          # PHB  (MVN écrase DBR)
        for tile_i, dst in copies:
            src = data_base + tile_i * 16          # adresse 16-bit (banque $80)
            c += bytes([0xA2, src & 0xFF, (src >> 8) & 0xFF])   # LDX #src
            c += bytes([0xA0, dst & 0xFF, (dst >> 8) & 0xFF])   # LDY #dst
            c += bytes([0xA9, 0x0F, 0x00])                       # LDA #$000F
            c += bytes([0x54, 0x7E, 0x80])                       # MVN dest=$7E,src=$80
        c += bytes([0xAB])                          # PLB
        jd = len(c); c += bytes([0x4C, 0x00, 0x00])# JMP done
        # Bloc PAGER (fenêtres WHO / ordres) : lettres anglaises sur les kanji
        pager_at = len(c)
        pj = []
        if pager:
            for addr, val in pager["sigs"]:
                c += bytes([0xAF, addr & 0xFF, (addr >> 8) & 0xFF, 0x7E])  # LDA $7E:sig
                c += bytes([0xC9, val & 0xFF, (val >> 8) & 0xFF])          # CMP #sig
                c += bytes([0xF0, 0x03])                                   # BEQ +3
                pj.append(len(c)); c += bytes([0x4C, 0x00, 0x00])          # JMP done
            src, dst, n = pager["src"], pager["dst"], pager["len"] - 1
            c += bytes([0x8B])                                             # PHB
            c += bytes([0xA2, src & 0xFF, (src >> 8) & 0xFF])              # LDX #src
            c += bytes([0xA0, dst & 0xFF, (dst >> 8) & 0xFF])              # LDY #dst
            c += bytes([0xA9, n & 0xFF, (n >> 8) & 0xFF])                  # LDA #len-1
            c += bytes([0x54, 0x7E, pager["src_bank"]])                    # MVN $7E,src
            c += bytes([0xAB])                                             # PLB
        done = len(c)
        # Épilogue original rejoué : PLY PLX PLA PLP RTS
        c += bytes([0x7A, 0xFA, 0x68, 0x28, 0x60])
        done_snes = HOOK_SNES + done
        pager_snes = HOOK_SNES + pager_at
        for j in (j1, j2):
            c[j + 1] = pager_snes & 0xFF; c[j + 2] = (pager_snes >> 8) & 0xFF
        for j in [jd] + pj:
            c[j + 1] = done_snes & 0xFF; c[j + 2] = (done_snes >> 8) & 0xFF
        return c

    code_len = len(build_code(0))                  # taille fixe
    data_base = HOOK_SNES + code_len
    code = build_code(data_base)
    assert len(code) == code_len
    blob = bytes(code) + b"".join(tiles)
    return blob


def apply(rom: bytearray, pager=None):
    # Restaure l'enveloppe $80:F8D8 si une build précédente l'avait détournée.
    if rom[WRAP_FILE:WRAP_FILE + 4] == WRAP_OLDHOOK:
        rom[WRAP_FILE:WRAP_FILE + 4] = WRAP_ORIG

    blob = assemble(pager)
    if HOOK_FILE + len(blob) > FREE_END_FILE:
        raise SystemExit(f"Dépassement zone libre $80 : {len(blob)} o "
                         f"(dispo {FREE_END_FILE - HOOK_FILE} o).")
    rom[HOOK_FILE:HOOK_FILE + len(blob)] = blob

    cur = rom[EXIT_FILE:EXIT_FILE + 4]
    if cur == EXIT_NEW:
        return True                                # déjà détourné (bloc réécrit ci-dessus)
    if cur != EXIT_ORIG:
        raise SystemExit(f"$80:F902 inattendu : {cur.hex()} (attendu {EXIT_ORIG.hex()})")
    rom[EXIT_FILE:EXIT_FILE + 4] = EXIT_NEW
    return True


def main():
    if not OUT.is_file():
        raise SystemExit(f"{OUT.name} introuvable — lancer build_full_translation.py")
    rom = bytearray(OUT.read_bytes())
    apply(rom)
    fix_checksum(rom)
    OUT.write_bytes(rom)
    blob = assemble()
    print(f"Écrit : {OUT.name}")
    print(f"  hook menu combat : {len(blob)} o @ $80:{HOOK_SNES:04X} "
          f"(dispo {FREE_END_FILE - HOOK_FILE} o)")
    print("  commandes : " + " / ".join(w for _, _, w in CMDS))


if __name__ == "__main__":
    main()
