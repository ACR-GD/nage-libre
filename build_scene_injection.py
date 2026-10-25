#!/usr/bin/env python3
"""Injection MULTI-SCÈNES à grande échelle (Nage Libre).

Toutes les scènes de dialogue/narration sont décompressées en `$7F:64C0` par
`$80:F8D8`, appelé depuis l'init narration `$83:80DB`. Juste avant ce JSL
($83:80FF), le registre **A = scene_idx** (base 0x030F = index de la table de
pointeurs source $8A:8000). C'est une clé EXACTE, sans collision : on hooke
$83:80FF, on garde A, on décompresse, puis on recopie les chaînes anglaises de
la bonne scène à leur offset dans le buffer.

Sûreté : chaque chaîne anglaise est bornée à `n_ids` (longueur EXACTE de la
chaîne japonaise d'origine) et terminée par `$FFFF`. Elle reste donc strictement
dans l'empreinte de la chaîne JP -> jamais de débordement sur le programme
d'opcodes. Les offsets sont validés (walk d'opcodes : offset « ligne de texte »
OU offset >= fin du programme) pour rejeter les faux positifs en zone programme.

Table (annuaire scene_idx -> section + données) : trop grosse pour la banque $83
(~1.8 Ko) -> placée en ROM ÉTENDUE à 2 Mo (banques $B0+, déjà déclarées par
l'en-tête). Le hook (~130 o) reste en banque $83.

Police : encodeur par paires (2 car./tuile 16x16) avec repli MONO-caractère
(1 car./tuile) pour les digrammes rares -> tient dans le pool d'IDs partagé quel
que soit le volume de texte.

apply(rom, alloc) est appelé par build_full_translation.py (allocateur partagé,
APRÈS menu/noms/clubs pour connaître le budget de police restant).
"""
import csv
import importlib.util
import struct
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT / "scripts"))

from patch_prologue_v3 import FONT, JP_SPACE  # noqa: E402
from nl_decompress import decompress, read_ptr_table  # noqa: E402

_spec = importlib.util.spec_from_file_location(
    "dp", ROOT / "scripts" / "decompile_prologue_script.py")
dp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(dp)

SCENES_DIR = ROOT / "docs" / "scenes"
ELLIPSIS = 0x02AA
DEST_BASE = 0x64C0
SCENE_BASE = 0x030F            # scene_idx du 1er enregistrement de la table

HOOK_POINT = 0x0180FF          # ROM offset de $83:80FF
HOOK_BANK = 0x83
HOOK_ADDR = 0xF8E3
HOOK_ROM = 0x01F8E3
FREE83_END = 0x01FFE0

# ROM étendue : annuaire + données en $B0:8000+ (l'en-tête déclare déjà 2 Mo)
EXP_FILE_START = 0x180000
EXP_FILE_END = 0x200000
BANK_SIZE = 0x8000

PAIR_BUDGET_MARGIN = 12        # garde-fou d'IDs de police

# Géométrie des boîtes de texte par opcode d'affichage : (colonnes demi-chasse,
# rangées visibles). Colonnes = $1144 - $1143 lus dans chaque handler :
# op01 : 8..$1E ; op23 : 1..$1E ; op0B/26/2B/3B : 1..$1F. La boîte n'affiche que
# 3 rangées (vérifié en jeu, op26/op2B : la 4e passe sous la bordure basse).
BOX_GEOMETRY = {0x01: (22, 3), 0x0B: (30, 3), 0x23: (29, 3),
                0x26: (30, 3), 0x2B: (30, 3), 0x3B: (30, 3)}
DEFAULT_GEOMETRY = (22, 3)     # autres opcodes : marges non lues, prudence


def off_to_snes(file_off):
    bank = 0x80 + file_off // BANK_SIZE
    addr = 0x8000 + (file_off % BANK_SIZE)
    return (bank << 16) | addr


# ---------------------------------------------------------------------------
# 1) Validation des offsets par scène (walk d'opcodes du buffer décompressé)
# ---------------------------------------------------------------------------
def _scene_validator(rom, src_off):
    """Renvoie (legit_offsets, prog_end, orig_len, geometry) pour une scène décompressée."""
    out, _ = decompress(rom, src_off, dst_limit=0x4000)
    n = len(out)

    def word(o):
        return out[o] | (out[o + 1] << 8) if o + 1 < n else 0xFFFF

    handlers = _scene_validator.handlers
    sizes = _scene_validator.sizes
    feats = _scene_validator.feats

    legit = set()
    pos = 0
    for _ in range(4000):
        opc = word(pos)
        if opc == 0xFFFF or opc not in handlers:
            break
        size = sizes.get(opc, 0) or 2
        nopr = (size - 2) // 2
        if feats[opc]["textline"] and nopr >= 1:
            o0 = word(pos + 2)
            if o0 >= 0x100:
                legit.add(o0)
        pos += size
    prog_end = pos

    def orig_len(o):
        k = 0
        while o + 2 * k < n and word(o + 2 * k) != 0xFFFF and k < 80:
            k += 1
        return k

    def geometry(o):
        """(cols, max_rows) de la boîte qui affiche la chaîne à l'offset `o` :
        opcodes « ligne de texte » dont le 1er opérande vaut `o` (balayage brut,
        le walk d'opcodes s'arrête tôt sur certaines scènes)."""
        ops = {word(q) for q in range(0, min(o, n) - 2, 2)
               if word(q + 2) == o and feats.get(word(q), {}).get("textline")}
        # chaîne partagée par plusieurs boîtes : la plus étroite l'emporte
        return min((BOX_GEOMETRY.get(op, DEFAULT_GEOMETRY) for op in ops),
                   default=DEFAULT_GEOMETRY)

    return legit, prog_end, orig_len, geometry


def _init_walk_tables():
    handlers = dp.opcode_handlers()
    _scene_validator.handlers = handlers
    _scene_validator.sizes = {k: dp.opcode_size(v) for k, v in handlers.items()}
    _scene_validator.feats = {k: dp.handler_features(v) for k, v in handlers.items()}


# ---------------------------------------------------------------------------
# 2) Chargement + validation des enregistrements traduits
# ---------------------------------------------------------------------------
def load_scene_records(rom):
    """{scene_idx: [(offset, en, slot, (cols, max_rows)), ...]} pour les scènes traduites valides."""
    _init_walk_tables()
    tbl = {i: off for i, _snes, off in read_ptr_table(rom, 0x600) if off}

    scenes = {}
    for path in sorted(SCENES_DIR.glob("scene_*.csv")):
        scene_idx = int(path.stem.split("_")[1], 16)
        src = tbl.get(scene_idx)
        if src is None or src >= len(rom):
            continue
        try:
            legit, prog_end, orig_len, geometry = _scene_validator(rom, src)
        except Exception:
            continue

        recs = []
        for r in csv.DictReader(path.open(encoding="utf-8")):
            en = (r.get("en") or "").strip()
            if not en:
                continue
            off = int(r["offset_hex"], 16)
            # rejette les faux positifs en zone programme (≠ offset de ligne réel)
            if off not in legit and off < prog_end:
                continue
            slot = orig_len(off)            # borne sûre = longueur JP d'origine
            if slot < 1:
                continue
            recs.append((off, en, slot, geometry(off)))
        if recs:
            scenes[scene_idx] = recs
    return scenes


# ---------------------------------------------------------------------------
# 3) Moteur de police matérielle 8x16 native (demi-chasse)
# ---------------------------------------------------------------------------
HW_BASE_ID = 0x0500
HW_HOOK_ADDR = 0xFF10
HW_HOOK_FILE = 0x7F10

# Table de correspondance caractère -> ID 16-bit
CHAR_TO_HW_ID = {chr(c): HW_BASE_ID + (c - 32) for c in range(32, 127)}
CHAR_TO_HW_ID['…'] = HW_BASE_ID + 95
CHAR_TO_HW_ID['—'] = HW_BASE_ID + 96
CHAR_TO_HW_ID['ー'] = CHAR_TO_HW_ID['-']
CHAR_TO_HW_ID['□'] = CHAR_TO_HW_ID['?']


def encode_hw(text):
    """Encode une chaîne de texte en IDs demi-chasse (8x16) natifs."""
    ids = []
    for ch in text:
        cid = CHAR_TO_HW_ID.get(ch)
        if cid is None:
            cid = CHAR_TO_HW_ID.get('?')
        ids.append(cid)
    return ids


def layout_rows(text, w):
    """Découpe le texte en rangées de <= `w` caractères sans couper les mots
    (un mot plus long que `w` est coupé en morceaux de `w`). '\n' force une rangée."""
    rows = []
    for para in text.replace("...", "…").split("\n"):
        cur = ""
        for word in para.split():
            while len(word) > w:
                if cur:
                    rows.append(cur)
                    cur = ""
                rows.append(word[:w])
                word = word[w:]
            if not cur:
                cur = word
            elif len(cur) + 1 + len(word) <= w:
                cur += " " + word
            else:
                rows.append(cur)
                cur = word
        if cur:
            rows.append(cur)
    return rows


def wrap_rows(text, cols=22, max_rows=3):
    """Choisit la largeur de wrapping : cols-2 puis cols-1 (marge droite plus
    équilibrée d'abord, ex. '…Hey, a samurai?!' / 'Why do I have to?!') ; garde la
    première qui tient en `max_rows` rangées, sinon la plus large (débordement).
    Jamais `cols` : une rangée pleine déclenche le retour à la ligne automatique du
    plotter $80:F433 (col >= $1144), et le $FFFE suivant laisserait une rangée vide."""
    for w in (cols - 2, cols - 1):
        rows = layout_rows(text, w)
        if len(rows) <= max_rows:
            return rows
    return rows


def wrap_encode(text, cols=22, max_rows=3):
    """Enveloppe et encode le texte en IDs demi-chasse (8x16) avec sauts de ligne propres ($FFFE).
    `cols` = largeur de la boîte en demi-chasse (op01 : $1E-8 = 22), `max_rows` =
    rangées visibles. Le moteur SNES ne coupe jamais les mots en deux."""
    rows = wrap_rows(text, cols, max_rows)
    ids = []
    for r_idx, row in enumerate(rows):
        ids.extend(encode_hw(row))
        if r_idx < len(rows) - 1:
            ids.append(NEWLINE_CODE)
    return ids


def encode_fit(text, slot=0, cols=22, max_rows=3):
    """Encode en bornant à `slot` IDs si non relocalisable. Coupe sur frontière de mot."""
    ids = wrap_encode(text, cols, max_rows)
    if len(ids) <= slot:
        return ids, False
    words = text.split(" ")
    while len(words) > 1:
        words.pop()
        cand = wrap_encode(" ".join(words), cols, max_rows)
        if len(cand) <= slot:
            return cand, True
    return ids[:slot], True


NEWLINE_CODE = 0xFFFE
NEWLINE_HOOK_ADDR = 0xFEE0
NEWLINE_ENTRY_ADDR = 0xF433
NEWLINE_ENTRY_FILE = 0x7433
NEWLINE_HOOK_FILE = 0x7EE0


def assemble_newline_hook():
    """Hook @ $80:FEE0 interceptant le code de saut de ligne $FFFE pour $80:F433."""
    c = bytearray()
    # 1. Préserve immédiatement les flags P et force A/XY en 16-bit
    c += bytes([0x08])                                # PHP
    c += bytes([0xC2, 0x30])                          # REP #$30

    # 2. Vérifie le code de saut de ligne ($FFFE)
    c += bytes([0xC9, 0xFE, 0xFF])                    # CMP #$FFFE
    c += bytes([0xF0, 0x0A])                          # BEQ handle_newline (+10)

    # Chemin normal : sauvegarde A/X/Y, charge X et saute à $80:F43C
    c += bytes([0x48])                                # PHA
    c += bytes([0xDA])                                # PHX
    c += bytes([0x5A])                                # PHY
    c += bytes([0xAE, 0x40, 0x02])                    # LDX $0240
    c += bytes([0x5C, 0x3C, 0xF4, 0x80])              # JML $80:F43C

    # handle_newline : avance la rangée et réinitialise la colonne
    c += bytes([0xE2, 0x20])                          # SEP #$20
    c += bytes([0xAD, 0x42, 0x11])                    # LDA $1142 (rangée courante)
    c += bytes([0x18, 0x69, 0x02])                    # CLC ; ADC #$02
    c += bytes([0xC9, 0x1F])                          # CMP #$1F
    c += bytes([0x30, 0x02])                          # BMI +2
    c += bytes([0xA9, 0x1E])                          # LDA #$1E
    c += bytes([0x8D, 0x42, 0x11])                    # STA $1142
    c += bytes([0xAD, 0x43, 0x11])                    # LDA $1143 (marge gauche)
    c += bytes([0x8D, 0x41, 0x11])                    # STA $1141 (colonne courante)
    c += bytes([0x28])                                # PLP (restaure flags et taille de l'appelant)
    c += bytes([0x60])                                # RTS
    return bytes(c)


def install_newline_hook(rom: bytearray):
    """Installe l'intercepteur de saut de ligne dans la banque $80."""
    hook = assemble_newline_hook()
    rom[NEWLINE_HOOK_FILE:NEWLINE_HOOK_FILE + len(hook)] = hook

    # Détournement à $80:F433 : JML $80:FEE0 + NOPs
    patch = bytearray([0x5C, NEWLINE_HOOK_ADDR & 0xFF, (NEWLINE_HOOK_ADDR >> 8) & 0xFF, 0x80])
    patch += bytes([0xEA] * 5)
    rom[NEWLINE_ENTRY_FILE:NEWLINE_ENTRY_FILE + len(patch)] = patch


def assemble_hw_hook():
    """Sous-routine à $80:FF10 testant si l'ID dans A est demi-chasse (8x16).
    Renvoie Carry = 0 si demi-chasse (< 0x0010 OU 0x0500..0x056F),
            Carry = 1 si pleine-chasse (0x0010..0x04FF OU >= 0x0570)."""
    c = bytearray()
    c += bytes([0xC9, 0x10, 0x00])      # CMP #$0010
    c += bytes([0x90, 0x0A])            # BCC +10 ($FF1F)
    c += bytes([0xC9, 0x00, 0x05])      # CMP #$0500
    c += bytes([0x90, 0x07])            # BCC +7  ($FF21)
    c += bytes([0xC9, 0x70, 0x05])      # CMP #$0570
    c += bytes([0xB0, 0x02])            # BCS +2  ($FF21)
    # $FF1F:
    c += bytes([0x18, 0x60])            # CLC ; RTS
    # $FF21:
    c += bytes([0x38, 0x60])            # SEC ; RTS
    return bytes(c)


def install_hw_hook(rom: bytearray):
    """Installe la sous-routine is_half_width à $80:FF10 et patche les 3 sites de $80:F390."""
    sub = assemble_hw_hook()
    rom[HW_HOOK_FILE:HW_HOOK_FILE + len(sub)] = sub

    # Site 1 : $80:F3AD (offset 0x73AD) - 5 octets
    rom[0x73AD:0x73AD + 5] = bytes([0x20, HW_HOOK_ADDR & 0xFF, (HW_HOOK_ADDR >> 8) & 0xFF, 0x90, 0x02])

    # Site 2 : $80:F3C6 (offset 0x73C6) - 5 octets
    rom[0x73C6:0x73C6 + 5] = bytes([0x20, HW_HOOK_ADDR & 0xFF, (HW_HOOK_ADDR >> 8) & 0xFF, 0xB0, 0x1E])

    # Site 3 : $80:F425 (offset 0x7425) - 6 octets
    rom[0x7425:0x7425 + 6] = bytes([0x20, HW_HOOK_ADDR & 0xFF, (HW_HOOK_ADDR >> 8) & 0xFF, 0xEA, 0xEA, 0xEA])


def install_hw_font(rom: bytearray):
    """Installe les tuiles 8x16 (32 octets 2bpp par caractère) pour tous les caractères
    supportés en ROM à partir de char_id_to_rom(0x0500) = 0x032000."""
    from patch_prologue_v3 import make_half_tile, char_id_to_rom
    for ch in FONT:
        if ch in CHAR_TO_HW_ID:
            cid = CHAR_TO_HW_ID[ch]
            data = make_half_tile(ch)
            off = char_id_to_rom(cid)
            rom[off:off + 32] = data


# ---------------------------------------------------------------------------
# 4) Hook scene_idx (banque $83) — annuaire 4 o/entrée en ROM étendue
# ---------------------------------------------------------------------------
def assemble_hook(dir_snes, base, ndir):
    """Hook @ $83:F8E3. A=scene_idx en entrée. Annuaire DIR (4 o/entrée :
    addrLo, addrHi, bank, 0) à l'adresse 24-bit `dir_snes` ; bank 0 = pas de
    section.
    Section format :
      [n_repoints, (ptr_pos, new_offset) * n_repoints, (dest_offset, count, ids…) * n_strings, FFFF]
    """
    DLO = dir_snes & 0xFFFF
    DHI = (dir_snes >> 16) & 0xFF
    c = bytearray()
    c += bytes([0x22, 0xD8, 0xF8, 0x80])              # JSL $80F8D8 (A préservé)
    c += bytes([0x08])                                # PHP
    c += bytes([0xC2, 0x30])                          # REP #$30
    c += bytes([0xDA, 0x5A])                          # PHX PHY
    c += bytes([0xA8])                                # TAY  (Y = scene_idx)
    # sauvegarde ZP (16-bit) : $09/$0A, $0B/$0C, $0D/$0E, $3C/$3D, $3E/$3F
    c += bytes([0xA5, 0x09, 0x48])                    # LDA $09 ; PHA
    c += bytes([0xA5, 0x0B, 0x48])                    # LDA $0B ; PHA
    c += bytes([0xA5, 0x0D, 0x48])                    # LDA $0D ; PHA
    c += bytes([0xA5, 0x3C, 0x48])                    # LDA $3C ; PHA
    c += bytes([0xA5, 0x3E, 0x48])                    # LDA $3E ; PHA
    # index annuaire = (scene_idx - base) ; borne
    c += bytes([0x98])                                # TYA
    c += bytes([0x38, 0xE9, base & 0xFF, (base >> 8) & 0xFF])  # SEC ; SBC #base
    jmp_done = []
    c += bytes([0x30, 0x00]); b_neg = len(c) - 1      # BMI done
    c += bytes([0xC9, ndir & 0xFF, (ndir >> 8) & 0xFF])  # CMP #ndir
    c += bytes([0xB0, 0x00]); b_ge = len(c) - 1       # BCS done
    c += bytes([0x0A, 0x0A])                          # ASL A ; ASL A  (*4)
    c += bytes([0xAA])                                # TAX
    # bank = DIR+2,X ; 0 => done
    c += bytes([0xBF, (DLO + 2) & 0xFF, ((DLO + 2) >> 8) & 0xFF, DHI])  # LDA.l DIR+2,X
    c += bytes([0x29, 0xFF, 0x00])                    # AND #$00FF
    c += bytes([0xF0, 0x00]); b_z = len(c) - 1        # BEQ done
    c += bytes([0x85, 0x3E])                          # STA $3E  (src bank)
    c += bytes([0xBF, DLO & 0xFF, (DLO >> 8) & 0xFF, DHI])  # LDA.l DIR,X (addr16)
    c += bytes([0x85, 0x3C])                          # STA $3C  (src addr)
    # $0B = $7F (bank dest), une fois
    c += bytes([0xE2, 0x20, 0xA9, 0x7F, 0x85, 0x0B, 0xC2, 0x20])  # SEP/LDA/STA/REP
    c += bytes([0xA0, 0x00, 0x00])                    # LDY #$0000  (index section)

    # --- Phase 1 : Repointage des opcodes bytecode pour lignes relocalisées ---
    c += bytes([0xB7, 0x3C])                          # LDA [$3C],Y (n_repoints)
    c += bytes([0xF0, 0x16])                          # BEQ skip_repoints (+22)
    c += bytes([0x85, 0x0C])                          # STA $0C (compteur)
    rp_loop = len(c)
    c += bytes([0xC8, 0xC8])                          # INY INY
    c += bytes([0xB7, 0x3C])                          # LDA [$3C],Y (ptr_pos)
    c += bytes([0x18, 0x69, 0xC0, 0x64])              # CLC ; ADC #$64C0
    c += bytes([0x85, 0x09])                          # STA $09
    c += bytes([0xC8, 0xC8])                          # INY INY
    c += bytes([0xB7, 0x3C])                          # LDA [$3C],Y (new_offset)
    c += bytes([0x87, 0x09])                          # STA [$09]
    c += bytes([0xC6, 0x0C])                          # DEC $0C
    c += bytes([0xD0, (rp_loop - (len(c) + 2)) & 0xFF]) # BNE rp_loop
    # skip_repoints:
    c += bytes([0xC8, 0xC8])                          # INY INY

    # --- Phase 2 : Copie des chaînes de texte ---
    rec = len(c)
    c += bytes([0xB7, 0x3C])                          # LDA [$3C],Y  (dest_offset)
    c += bytes([0xC9, 0xFF, 0xFF])                    # CMP #$FFFF
    c += bytes([0xD0, 0x03])                          # BNE +3
    jmp_done.append(len(c)); c += bytes([0x4C, 0x00, 0x00])  # JMP done
    c += bytes([0x18, 0x69, 0xC0, 0x64])              # CLC ; ADC #$64C0
    c += bytes([0x85, 0x09])                          # STA $09  (dest addr)
    c += bytes([0xC8, 0xC8])                          # INY INY
    c += bytes([0xB7, 0x3C])                          # LDA [$3C],Y  (count)
    c += bytes([0x0A, 0x85, 0x0C])                    # ASL A ; STA $0C (octets)
    c += bytes([0xC8, 0xC8])                          # INY INY
    c += bytes([0xA2, 0x00, 0x00])                    # LDX #$0000  (octets copiés)
    cp = len(c)
    c += bytes([0xB7, 0x3C])                          # LDA [$3C],Y  (id)
    c += bytes([0x87, 0x09])                          # STA [$09]
    c += bytes([0xA5, 0x09, 0x18, 0x69, 0x02, 0x00, 0x85, 0x09])  # $09 += 2
    c += bytes([0xC8, 0xC8])                          # INY INY
    c += bytes([0xE8, 0xE8])                          # INX INX
    c += bytes([0xE4, 0x0C])                          # CPX $0C
    c += bytes([0x90, (cp - (len(c) + 2)) & 0xFF])    # BCC cp
    c += bytes([0x80, (rec - (len(c) + 2)) & 0xFF])   # BRA rec
    done = len(c)
    c[b_neg] = (done - (b_neg + 1)) & 0xFF
    c[b_ge] = (done - (b_ge + 1)) & 0xFF
    c[b_z] = (done - (b_z + 1)) & 0xFF
    done_snes = HOOK_ADDR + done
    for j in jmp_done:
        c[j + 1] = done_snes & 0xFF
        c[j + 2] = (done_snes >> 8) & 0xFF
    # restauration ZP (ordre inverse)
    c += bytes([0x68, 0x85, 0x3E])                    # PLA ; STA $3E
    c += bytes([0x68, 0x85, 0x3C])                    # PLA ; STA $3C
    c += bytes([0x68, 0x85, 0x0D])                    # PLA ; STA $0D
    c += bytes([0x68, 0x85, 0x0B])                    # PLA ; STA $0B
    c += bytes([0x68, 0x85, 0x09])                    # PLA ; STA $09
    c += bytes([0x7A, 0xFA])                          # PLY PLX
    c += bytes([0x28, 0x6B])                          # PLP RTL
    return bytes(c)


# ---------------------------------------------------------------------------
# 5) apply() — encode, place annuaire+données en $B0+, écrit le hook
# ---------------------------------------------------------------------------
def apply(rom: bytearray, alloc=None):
    scenes = load_scene_records(rom)
    if not scenes:
        return {"scenes": 0, "lines": 0, "truncated": 0, "bytes": 0}

    # 1. Installe la police matérielle demi-chasse (8x16) et les hooks moteur en banque $80
    install_hw_font(rom)
    install_hw_hook(rom)
    install_newline_hook(rom)

    # Table des pointeurs de scènes pour décompresser et inspecter le bytecode
    tbl = {i: off for i, _s, off in read_ptr_table(rom, 0x600) if off}

    # Encodage avec relocalisation pour les lignes qui dépassent
    encoded = {}            # scene_idx -> (repoints, [(dest_offset, ids+FFFF)])
    truncated = 0
    overflow = []           # (scene_idx, offset, cols, max_rows, rangées, en)
    relocated_count = 0

    for sidx, recs in scenes.items():
        src = tbl.get(sidx)
        out, _ = decompress(rom, src, dst_limit=0x4000)
        w = lambda o: out[o] | (out[o+1] << 8) if o + 1 < len(out) else 0xFFFF

        # Recherche de la fin du programme d'opcodes (premier FFFF aligné)
        prog_end = 0
        for p in range(0, len(out) - 1, 2):
            if w(p) == 0xFFFF:
                prog_end = p
                break

        # Curseur d'offset WRAM pour les nouvelles chaînes au-delà du buffer
        cur_end = len(out)
        if cur_end % 2 != 0:
            cur_end += 1

        repoints = []
        string_records = []

        for off, en, slot, (cols, max_rows) in recs:
            full_ids = wrap_encode(en, cols, max_rows)
            n_rows = len(wrap_rows(en, cols, max_rows))
            if n_rows > max_rows:
                overflow.append((sidx, off, cols, max_rows, n_rows, en))
            if len(full_ids) <= slot:
                # Tient sur place
                string_records.append((off, full_ids + [0xFFFF]))
            else:
                # Dépasse la longueur JP d'origine : on cherche les références dans le programme
                ptrs = [p for p in range(0, prog_end, 2) if w(p) == off]
                if ptrs:
                    # Relocalisation à la fin du buffer décompressé
                    new_off = cur_end
                    cur_end += (len(full_ids) + 1) * 2
                    for p in ptrs:
                        repoints.append((p, new_off))
                    string_records.append((new_off, full_ids + [0xFFFF]))
                    relocated_count += 1
                else:
                    # Repli exceptionnel si aucun pointeur trouvé dans prog_end
                    ids, was_trunc = encode_fit(en, slot, cols, max_rows)
                    if was_trunc:
                        truncated += 1
                    string_records.append((off, ids + [0xFFFF]))

        encoded[sidx] = (repoints, string_records)

    idxs = sorted(encoded)
    base = SCENE_BASE
    ndir = max(idxs) - base + 1

    # étend la ROM à 2 Mo si besoin
    if len(rom) < EXP_FILE_END:
        rom.extend(b"\xFF" * (EXP_FILE_END - len(rom)))

    # annuaire (4 o/entrée) en $B0:8000 ; sections bin-packées sans franchir de
    # frontière de banque (32 Ko) -> [src],Y reste dans la banque.
    dir_file = EXP_FILE_START
    dir_snes = off_to_snes(dir_file)
    dir_bytes = bytearray(ndir * 4)        # 00.. = pas de section

    cursor = dir_file + len(dir_bytes)
    for sidx in idxs:
        repoints, str_recs = encoded[sidx]
        sec = bytearray()

        # En-tête : nombre de repoints
        sec += struct.pack("<H", len(repoints))
        for ptr_pos, new_off in repoints:
            sec += struct.pack("<HH", ptr_pos, new_off)

        # Chaînes de texte
        for dest_off, ids in str_recs:
            sec += struct.pack("<HH", dest_off, len(ids))
            for cid in ids:
                sec += struct.pack("<H", cid)
        sec += struct.pack("<H", 0xFFFF)

        # ne pas franchir la frontière de banque
        bank_end = (cursor // BANK_SIZE + 1) * BANK_SIZE
        if cursor + len(sec) > bank_end:
            cursor = bank_end
        if cursor + len(sec) > EXP_FILE_END:
            raise SystemExit("Dépassement ROM étendue (sections de scènes).")
        snes = off_to_snes(cursor)
        rom[cursor:cursor + len(sec)] = sec
        e = (sidx - base) * 4
        dir_bytes[e] = snes & 0xFF
        dir_bytes[e + 1] = (snes >> 8) & 0xFF
        dir_bytes[e + 2] = (snes >> 16) & 0xFF
        cursor += len(sec)

    rom[dir_file:dir_file + len(dir_bytes)] = dir_bytes

    # hook scènes en banque $83 + redirection $83:80FF
    hook = assemble_hook(dir_snes, base, ndir)
    if HOOK_ROM + len(hook) > FREE83_END:
        raise SystemExit(f"Hook scènes trop gros pour banque $83 ({len(hook)} o).")
    rom[HOOK_ROM:HOOK_ROM + len(hook)] = hook
    rom[HOOK_POINT:HOOK_POINT + 4] = bytes(
        [0x22, HOOK_ADDR & 0xFF, (HOOK_ADDR >> 8) & 0xFF, HOOK_BANK])

    return {
        "scenes": len(idxs),
        "lines": sum(len(str_recs) for _, str_recs in encoded.values()),
        "truncated": truncated,
        "overflow": overflow,
        "relocated": relocated_count,
        "bytes": cursor - dir_file,
        "hook": len(hook),
        "pairs": len(CHAR_TO_HW_ID),
    }
