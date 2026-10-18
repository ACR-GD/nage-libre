#!/usr/bin/env python3
"""Boîte à outils PyGhidra réutilisable pour reverse-engineer des jeux Super Nintendo
(65816) en vue d'une traduction (JP -> EN, EN -> FR).

Pensée pour être copiée telle quelle dans n'importe quel projet de ROM-hacking SNES.
Elle combine :

  * Analyse de l'en-tête + détection automatique du mapping (LoROM / HiROM /
    ExHiROM) et de l'éventuel en-tête copieur SMC de 512 octets.
  * Conversions SNES <-> offset fichier dans les deux sens.
  * Des SCANNERS HEURISTIQUES en Python pur (sans Ghidra, donc rapides) qui
    repèrent les routines les plus utiles à traduire :
        - afficheurs de chaînes  (boucle : charge via pointeur, compare à un
          terminateur, branche)  -> où le texte est rendu ;
        - tables de pointeurs    (2 ou 3 octets)                -> où sont les
          scripts / chaînes ;
        - uploads DMA -> VRAM    (écritures $2116/$2118 + $420B) -> où la police
          / les tuiles sont chargées.
  * GRAPHISMES : décodage de tuiles SNES (2/4/8 bpp + Mode7) et rendu PNG, pour
    extraire les graphismes contenant du texte (logos, écrans-titres, libellés).
  * COMPRESSION : carte d'entropie (blobs compressés candidats) + détection
    heuristique de décompresseurs avec type deviné (RLE / LZSS / bit-packed /
    LZ custom). Méthodologie complète : docs/snes_compression_id.md.
  * L'intégration Ghidra (chargée à la demande) : map mémoire correct par banque,
    pose des vecteurs (RESET/NMI/IRQ), désassemble à une adresse, et peut
    SAUVEGARDER un projet Ghidra ouvrable dans l'UI (labels des routines trouvées).

Exemples :
    # info + vecteurs + heuristiques, rapport texte sur la sortie standard
    python3 scripts/snes_re_toolkit.py jeu.sfc

    # scanners seuls (aucun Ghidra requis), rapport markdown
    python3 scripts/snes_re_toolkit.py jeu.sfc --find-printers --find-tables \\
            --find-dma --report rapport.md

    # désassemble 40 instructions à $80:8000 et à $80:F8D8
    python3 scripts/snes_re_toolkit.py jeu.sfc --disasm 808000,40 --disasm 80F8D8,40

    # graphismes + compression : rendre une zone, lister blobs et décompresseurs
    python3 scripts/snes_re_toolkit.py jeu.sfc --gfx 0x28000,0x2000,2,32 --out font.png
    python3 scripts/snes_re_toolkit.py jeu.sfc --entropy --find-decompressors --find-dma
    python3 scripts/snes_re_toolkit.py jeu.sfc --gfx-bin dump_decompresse.bin,4,16 --out dump.png

    # construit + sauvegarde un projet Ghidra (ouvrable dans la GUI)
    python3 scripts/snes_re_toolkit.py jeu.sfc --save-project ./ghidra_proj:MonJeu --analyze

Pré-requis Ghidra (uniquement pour --vectors/--disasm/--save-project/--analyze) :
    pip install pyghidra
    export GHIDRA_INSTALL_DIR=/chemin/vers/ghidra   (sinon valeur par défaut ci-dessous)
"""
import argparse
import os
import struct
import sys
from pathlib import Path

os.environ.setdefault(
    "GHIDRA_INSTALL_DIR", "/opt/homebrew/Cellar/ghidra/12.1.1/libexec")

GHIDRA_LANG = "65816:LE:16:default"

# Opcodes 65816 d'intérêt pour les scanners (chargement indirect via pointeur).
LOAD_VIA_PTR = {
    0xA7: "LDA [dp]",
    0xB7: "LDA [dp],Y",
    0xB2: "LDA (dp)",
    0xB1: "LDA (dp),Y",
    0xBF: "LDA addr_long,X",
    0xBD: "LDA addr,X",
    0xB9: "LDA addr,Y",
}
CMP_IMM = 0xC9            # CMP #imm  (test de terminateur)
BRANCHES = {0xF0: "BEQ", 0xD0: "BNE", 0x80: "BRA", 0x90: "BCC", 0xB0: "BCS"}


# ===========================================================================
# 1. ROM : en-tête copieur, mapping, en-tête interne
# ===========================================================================
def strip_smc_header(data: bytes):
    """Retire l'en-tête copieur SMC de 512 o si présent. Renvoie (data, had_smc)."""
    if len(data) % 0x8000 == 0x200:
        return data[0x200:], True
    return data, False


def _score_header(data: bytes, base: int) -> int:
    """Score de plausibilité d'un en-tête interne SNES à l'offset `base`."""
    if base + 0x30 > len(data):
        return -1
    score = 0
    chk = data[base + 0x1E] | (data[base + 0x1F] << 8)
    cmp = data[base + 0x1C] | (data[base + 0x1D] << 8)
    if (chk ^ cmp) == 0xFFFF and chk != 0:
        score += 8
    reset = data[base + 0x3C] | (data[base + 0x3D] << 8)
    if reset >= 0x8000:
        score += 4
    title = data[base:base + 21]
    if all(0x20 <= b < 0x7F or b in (0x00,) for b in title):
        score += 2
    mapper = data[base + 0x15]
    if mapper in (0x20, 0x21, 0x23, 0x30, 0x31, 0x35):
        score += 2
    return score


def detect_mapping(data: bytes, forced: str = "auto"):
    """Renvoie 'lorom' | 'hirom' | 'exhirom' (header interne à 0x7FC0/0xFFC0/0x40FFC0)."""
    if forced != "auto":
        return forced
    cands = {"lorom": 0x7FC0, "hirom": 0xFFC0, "exhirom": 0x40FFC0}
    best, best_s = "lorom", -2
    for name, base in cands.items():
        s = _score_header(data, base)
        if s > best_s:
            best, best_s = name, s
    return best


def header_base(mapping: str) -> int:
    return {"lorom": 0x7FC0, "hirom": 0xFFC0, "exhirom": 0x40FFC0}[mapping]


def parse_header(data: bytes, mapping: str) -> dict:
    b = header_base(mapping)
    title = data[b:b + 21].decode("shift_jis", "replace").rstrip("\x00 ")
    rom_kb = (1 << data[b + 0x17]) if data[b + 0x17] < 0x20 else 0
    ram_kb = (1 << data[b + 0x18]) if data[b + 0x18] < 0x20 else 0
    vectors = {}
    for name, off in (("COP", 0x24), ("BRK", 0x26), ("ABORT", 0x28),
                      ("NMI", 0x2A), ("RESET", 0x3C), ("IRQ", 0x2E),
                      ("NMI_E", 0x3A), ("IRQ_E", 0x3E)):
        vectors[name] = data[b + off] | (data[b + off + 1] << 8)
    return {
        "title": title,
        "mapper": data[b + 0x15],
        "rom_type": data[b + 0x16],
        "rom_kb": rom_kb,
        "ram_kb": ram_kb,
        "region": data[b + 0x19],
        "checksum": data[b + 0x1E] | (data[b + 0x1F] << 8),
        "complement": data[b + 0x1C] | (data[b + 0x1D] << 8),
        "vectors": vectors,
    }


# ---- conversions SNES <-> fichier (selon mapping) ----
def snes_to_file(snes: int, mapping: str):
    bank = (snes >> 16) & 0xFF
    addr = snes & 0xFFFF
    if mapping == "lorom":
        if addr < 0x8000:
            return None
        return ((bank & 0x7F) * 0x8000) + (addr - 0x8000)
    # hirom / exhirom
    if bank in range(0x40, 0x7E) or bank >= 0xC0:
        return ((bank & 0x3F) * 0x10000) + addr
    if addr >= 0x8000:                      # miroir $80-$BF:8000-FFFF
        return ((bank & 0x3F) * 0x10000) + addr
    return None


def file_to_snes(off: int, mapping: str):
    if mapping == "lorom":
        bank = 0x80 + (off // 0x8000)
        return (bank << 16) | (0x8000 + (off % 0x8000))
    bank = 0xC0 + (off // 0x10000)
    return (bank << 16) | (off % 0x10000)


def fmt_snes(snes: int) -> str:
    return f"${(snes >> 16) & 0xFF:02X}:{snes & 0xFFFF:04X}"


# ===========================================================================
# 2. Scanners heuristiques (Python pur — aucun Ghidra requis)
# ===========================================================================
def find_string_printers(data: bytes, mapping: str, window: int = 24, limit: int = 60):
    """Repère les boucles d'affichage de texte : un chargement via pointeur suivi,
    dans une petite fenêtre, d'un CMP #imm (terminateur) et d'un branchement, le
    tout dans une boucle (branche arrière). Renvoie une liste de candidats."""
    out = []
    n = len(data)
    for i in range(n - window):
        op = data[i]
        if op not in LOAD_VIA_PTR:
            continue
        seg = data[i:i + window]
        # cherche CMP #imm
        jc = seg.find(bytes([CMP_IMM]))
        if jc < 2 or jc + 2 >= len(seg):
            continue
        term = seg[jc + 1]
        # branchement juste après le CMP (terminateur)
        bpos = jc + 2
        if seg[bpos] not in BRANCHES:
            continue
        # présence d'une branche arrière (boucle) dans la fenêtre
        has_loop = any(
            seg[k] in (0x80, 0xD0, 0xF0, 0x90, 0xB0) and seg[k + 1] >= 0x80
            for k in range(0, len(seg) - 1))
        if not has_loop:
            continue
        snes = file_to_snes(i, mapping)
        out.append({
            "file": i, "snes": snes, "load": LOAD_VIA_PTR[op],
            "term": term, "branch": BRANCHES[seg[bpos]],
        })
        if len(out) >= limit:
            break
    return out


def find_pointer_tables(data: bytes, mapping: str, min_entries: int = 16,
                        limit: int = 80):
    """Détecte les tables de pointeurs 2 octets (intra-banque) et 3 octets (long).
    Une table = >= min_entries entrées dont les cibles tombent dans la ROM."""
    out = []
    n = len(data)
    rom_kb = max(8, n // 1024)

    def valid_addr(addr):
        return addr >= 0x8000 if mapping == "lorom" else True

    # --- 3 octets (pointeurs long) ---
    i = 0
    while i < n - 3 * min_entries:
        cnt = 0
        j = i
        while j + 3 <= n:
            addr = data[j] | (data[j + 1] << 8)
            bank = data[j + 2]
            if addr in (0x0000, 0xFFFF):          # padding -> rupture
                break
            snes = (bank << 16) | addr
            if not (0x80 <= bank <= 0xFF or 0x00 <= bank <= 0x7D):
                break
            fo = snes_to_file(snes, mapping)
            if fo is None or fo >= n:
                break
            cnt += 1
            j += 3
        if cnt >= min_entries:
            out.append({"file": i, "snes": file_to_snes(i, mapping),
                        "stride": 3, "entries": cnt})
            i = j
        else:
            i += 3
        if len(out) >= limit:
            break

    # --- 2 octets (intra-banque) ; 0xFFFF/0x0000 rompent la série (padding) ---
    i = 0
    while i < n - 2 * min_entries:
        cnt = 0
        j = i
        while j + 2 <= n:
            addr = data[j] | (data[j + 1] << 8)
            if addr in (0x0000, 0xFFFF) or not valid_addr(addr):
                break
            cnt += 1
            j += 2
        if cnt >= min_entries:
            out.append({"file": i, "snes": file_to_snes(i, mapping),
                        "stride": 2, "entries": cnt})
            i = j
        else:
            i += 2
        if len(out) >= limit * 2:
            break
    return out


def find_vram_dma(data: bytes, mapping: str, limit: int = 80):
    """Repère les écritures de registres clés des uploads graphiques :
       STA $2116/$2117 (adresse VRAM), STA $4300.. (params DMA), STA $420B (go)."""
    targets = {0x2116: "VMADDL", 0x2117: "VMADDH", 0x2118: "VMDATAL",
               0x420B: "MDMAEN", 0x4300: "DMAP0", 0x4302: "A1T0L"}
    out = []
    n = len(data)
    for i in range(n - 3):
        # STA abs = 8D lo hi  ; STA long = 8F lo hi bank
        if data[i] == 0x8D:
            reg = data[i + 1] | (data[i + 2] << 8)
            if reg in targets:
                out.append({"file": i, "snes": file_to_snes(i, mapping),
                            "reg": targets[reg], "regaddr": reg})
                if len(out) >= limit:
                    break
    return out


# ===========================================================================
# 2b. Graphismes : décodage de tuiles SNES + rendu PNG
# ===========================================================================
# Formats planaires SNES (8x8) : 2bpp=16 o, 4bpp=32 o, 8bpp=64 o ; Mode7=64 o
# linéaire (1 octet/pixel). Texte « cuit » dans des graphismes (logos, « PUSH
# START », libellés de menu) -> à extraire pour traduire/redessiner.
TILE_SIZE = {"2": 16, "4": 32, "8": 64, "m7": 64}


def _decode_planar(seg, bpp):
    """Renvoie 8x8 indices de couleur pour une tuile planaire (bpp = 2/4/8)."""
    px = [[0] * 8 for _ in range(8)]
    planes = bpp
    for y in range(8):
        for pair in range(planes // 2):
            b0 = seg[pair * 16 + y * 2]
            b1 = seg[pair * 16 + y * 2 + 1]
            for x in range(8):
                bit = 7 - x
                px[y][x] |= ((b0 >> bit) & 1) << (pair * 2)
                px[y][x] |= ((b1 >> bit) & 1) << (pair * 2 + 1)
    return px


def _decode_m7(seg):
    return [[seg[y * 8 + x] for x in range(8)] for y in range(8)]


def render_tiles(data, bpp="4", per_row=16, scale=2, max_tiles=None, palette=None):
    """Rend `data` comme une planche de tuiles 8x8 -> image PIL (niveaux de gris
    par défaut, ou `palette` = liste de (r,g,b) indexée par couleur)."""
    from PIL import Image
    size = TILE_SIZE[bpp]
    ntiles = len(data) // size
    if max_tiles:
        ntiles = min(ntiles, max_tiles)
    if ntiles == 0:
        raise SystemExit("Pas assez de données pour une tuile.")
    rows = (ntiles + per_row - 1) // per_row
    img = Image.new("RGB", (per_row * 8, rows * 8), (40, 40, 40))
    pix = img.load()
    maxv = (1 << (8 if bpp == "m7" else int(bpp))) - 1
    for t in range(ntiles):
        seg = data[t * size:(t + 1) * size]
        cells = _decode_m7(seg) if bpp == "m7" else _decode_planar(seg, int(bpp))
        ox, oy = (t % per_row) * 8, (t // per_row) * 8
        for y in range(8):
            for x in range(8):
                v = cells[y][x]
                if palette and v < len(palette):
                    pix[ox + x, oy + y] = palette[v]
                else:
                    g = v * 255 // maxv if maxv else 0
                    pix[ox + x, oy + y] = (g, g, g)
    if scale != 1:
        img = img.resize((img.width * scale, img.height * scale), Image.NEAREST)
    return img


# ===========================================================================
# 2c. Compression : entropie (blobs compressés) + détection de décompresseurs
# ===========================================================================
def entropy_regions(data, block=0x100, thresh=6.8):
    """Régions à FORTE entropie (>= thresh bits/octet) = données compressées ou
    déjà denses. Indice (pas une preuve) de blob compressé. Renvoie [(off,len,H)]."""
    import math
    from collections import Counter
    regions = []
    start = end = None
    hmax = 0.0
    for i in range(0, len(data) - block, block):
        seg = data[i:i + block]
        c = Counter(seg)
        H = -sum((v / block) * math.log2(v / block) for v in c.values())
        if H >= thresh:
            if start is None:
                start, hmax = i, H
            end = i + block
            hmax = max(hmax, H)
        elif start is not None:
            regions.append((start, end - start, hmax))
            start = None
    if start is not None:
        regions.append((start, end - start, hmax))
    return regions


# Opcodes utiles à la détection de décompresseurs
SHIFT_OPS = {0x4A, 0x0A, 0x2A, 0x6A}          # LSR / ASL / ROL / ROR (sur A)
IND_LOAD = {0xA7, 0xB7, 0xB1, 0xB2}           # LDA [dp]/[dp],Y/(dp),Y/(dp)
IND_STORE = {0x87, 0x97, 0x91, 0x92}          # STA …
BACK_BRANCH = {0x80, 0xD0, 0xF0, 0x90, 0xB0}  # BRA/BNE/BEQ/BCC/BCS (offset < 0)


def classify_decompressor(data, off, span=0x200):
    """Devine le type de compression d'après la structure du code à `off`."""
    seg = data[off:off + span]
    nshift = sum(1 for b in seg if b in SHIFT_OPS)
    nload = sum(1 for b in seg if b in IND_LOAD)
    nstore = sum(1 for b in seg if b in IND_STORE)
    # copie « fenêtre » LZ : lecture indexée d'un tampon récemment écrit
    abs_copy = sum(1 for k in range(len(seg) - 3)
                   if seg[k] in (0xBD, 0xB9, 0xBF) and seg[k + 3] in (0x9D, 0x99, 0x9F))
    has_window = (nload and nstore) or abs_copy
    if nshift >= 4 and has_window:
        guess = "LZ + lecteur de bits (LZSS/Nintendo-LZ ou custom à nibbles/bits)"
    elif nshift >= 4:
        guess = "compression à bits (Huffman/codes de longueur variable ?)"
    elif has_window and nshift < 2:
        guess = "LZSS octet (back-reference, drapeaux par octet)"
    elif nstore >= 2 and nshift < 2 and not has_window:
        guess = "RLE (répétition d'octets)"
    else:
        guess = "indéterminé (inspecter au désassembleur)"
    return {"shifts": nshift, "ind_load": nload, "ind_store": nstore,
            "window_copy": has_window, "guess": guess}


def find_decompressors(data, mapping, window=0x60, min_shift=5, limit=40):
    """Repère les routines ressemblant à un décompresseur : grappe d'opérations de
    décalage (lecteur de bits) + copie « fenêtre » (LZ) + boucle arrière.

    HEURISTIQUE BRUITÉE et incomplète : les décompresseurs à TABLE DE SAUT
    (`JSR (table,X)`, comme $80:F8D8 dans Nage Libre) sont éclatés en
    sous-routines et passent sous le radar. Pour ceux-là, utiliser la méthode du
    trace DMA->WRAM (voir docs/snes_compression_id.md)."""
    shift_pos = [k for k, b in enumerate(data) if b in SHIFT_OPS]
    sset = shift_pos
    out, seen = [], -window
    import bisect
    for s in shift_pos:
        if s - seen < window:                       # dédoublonne les grappes proches
            continue
        # nb de décalages dans [s, s+window)
        hi = bisect.bisect_left(sset, s + window)
        lo = bisect.bisect_left(sset, s)
        if hi - lo < min_shift:
            continue
        seg = data[s:s + window]
        loop = any(seg[k] in BACK_BRANCH and seg[k + 1] >= 0x80
                   for k in range(len(seg) - 1))
        info = classify_decompressor(data, s)
        if not loop or not info["window_copy"]:
            continue
        info.update({"file": s, "snes": file_to_snes(s, mapping)})
        out.append(info)
        seen = s
        if len(out) >= limit:
            break
    return out


# ===========================================================================
# 3. Intégration Ghidra (importée à la demande)
# ===========================================================================
def _start_ghidra():
    import pyghidra
    pyghidra.start()


def build_program(data: bytes, mapping: str, name: str):
    """Construit un ProgramDB 65816 et y mappe la ROM banque par banque selon le
    mapping. Renvoie (prog, api, consumer)."""
    from ghidra.program.model.lang import LanguageID
    from ghidra.program.database import ProgramDB
    from ghidra.program.util import DefaultLanguageService
    from ghidra.program.flatapi import FlatProgramAPI
    from ghidra.util.task import TaskMonitor
    import java.lang.Object as JObject

    lang = DefaultLanguageService.getLanguageService().getLanguage(
        LanguageID(GHIDRA_LANG))
    consumer = JObject()
    prog = ProgramDB(name, lang, lang.getDefaultCompilerSpec(), consumer)
    api = FlatProgramAPI(prog)
    space = prog.getAddressFactory().getDefaultAddressSpace()
    mem = prog.getMemory()

    tx = prog.startTransaction("map")
    try:
        if mapping == "lorom":
            nb = (len(data) + 0x7FFF) // 0x8000
            for blk in range(nb):
                ro = blk * 0x8000
                chunk = data[ro:ro + 0x8000]
                bank = 0x80 + blk
                addr = space.getAddress((bank << 16) | 0x8000)
                b = mem.createInitializedBlock(
                    f"ROM_{bank:02X}", addr, len(chunk), 0, TaskMonitor.DUMMY, False)
                mem.setBytes(addr, chunk)
                b.setExecute(True)
        else:
            nb = (len(data) + 0xFFFF) // 0x10000
            for blk in range(nb):
                ro = blk * 0x10000
                chunk = data[ro:ro + 0x10000]
                bank = 0xC0 + blk
                addr = space.getAddress((bank << 16))
                b = mem.createInitializedBlock(
                    f"ROM_{bank:02X}", addr, len(chunk), 0, TaskMonitor.DUMMY, False)
                mem.setBytes(addr, chunk)
                b.setExecute(True)
    finally:
        prog.endTransaction(tx, True)
    return prog, api, consumer


def label_and_disassemble(prog, api, snes_points: dict):
    """Désassemble et pose un label (symbole) à chaque (label -> snes)."""
    from ghidra.util.task import TaskMonitor
    from ghidra.program.model.symbol import SourceType
    space = prog.getAddressFactory().getDefaultAddressSpace()
    tx = prog.startTransaction("disasm")
    try:
        st = prog.getSymbolTable()
        for label, snes in snes_points.items():
            a = space.getAddress(snes)
            api.disassemble(a)
            try:
                st.createLabel(a, label, SourceType.USER_DEFINED)
            except Exception:
                pass
    finally:
        prog.endTransaction(tx, True)


def disasm_text(prog, api, snes: int, n: int):
    space = prog.getAddressFactory().getDefaultAddressSpace()
    a = space.getAddress(snes)
    tx = prog.startTransaction("d")
    try:
        api.disassemble(a)
    finally:
        prog.endTransaction(tx, True)
    ins = prog.getListing().getInstructionAt(a)
    lines = []
    for _ in range(n):
        if ins is None:
            break
        lines.append(f"  {ins.getAddress()}  {ins}")
        ins = ins.getNext()
    return lines


def analyze(prog):
    from ghidra.app.plugin.core.analysis import AutoAnalysisManager
    from ghidra.util.task import TaskMonitor
    mgr = AutoAnalysisManager.getAnalysisManager(prog)
    tx = prog.startTransaction("analyze")
    try:
        mgr.initializeOptions()
        mgr.reAnalyzeAll(None)
        mgr.startAnalysis(TaskMonitor.DUMMY)
    finally:
        prog.endTransaction(tx, True)


def save_project(prog, proj_dir: str, proj_name: str):
    from ghidra.base.project import GhidraProject
    from ghidra.util.task import TaskMonitor
    Path(proj_dir).mkdir(parents=True, exist_ok=True)
    gp = GhidraProject.createProject(proj_dir, proj_name, False)
    gp.saveAs(prog, "/", prog.getName(), True)
    gp.close()


# ===========================================================================
# 4. Rapport / CLI
# ===========================================================================
def vectors_to_snes(hdr: dict, mapping: str):
    """Les vecteurs (RESET/NMI/IRQ) sont des adresses 16-bit en banque 0 ; en
    LoROM/HiROM le code vit en banque $80/$C0 -> on remappe pour le désassemblage."""
    bank = 0x80 if mapping == "lorom" else 0xC0
    pts = {}
    for name in ("RESET", "NMI", "IRQ"):
        v = hdr["vectors"][name]
        if v >= 0x8000:
            pts[name] = (bank << 16) | v
    return pts


def main():
    p = argparse.ArgumentParser(description="Boîte à outils PyGhidra pour le reverse SNES.")
    p.add_argument("rom", type=Path)
    p.add_argument("--map", default="auto", choices=["auto", "lorom", "hirom", "exhirom"])
    p.add_argument("--info", action="store_true", help="en-tête + mapping")
    p.add_argument("--vectors", action="store_true", help="désassemble RESET/NMI/IRQ (Ghidra)")
    p.add_argument("--find-printers", action="store_true")
    p.add_argument("--find-tables", action="store_true")
    p.add_argument("--find-dma", action="store_true")
    p.add_argument("--entropy", action="store_true",
                   help="régions à forte entropie (blobs compressés candidats)")
    p.add_argument("--find-decompressors", action="store_true",
                   help="routines ressemblant à un décompresseur + type deviné")
    p.add_argument("--gfx", metavar="OFF,LEN,BPP,W",
                   help="rend la ROM (offset FICHIER hex) en tuiles -> PNG "
                        "(BPP=2/4/8/m7, W=tuiles/ligne)")
    p.add_argument("--gfx-bin", metavar="PATH,BPP,W",
                   help="rend un binaire externe (ex. dump décompressé) en tuiles")
    p.add_argument("--out", type=Path, default=None, help="chemin du PNG de sortie")
    p.add_argument("--disasm", action="append", default=[],
                   metavar="SNES,LEN", help="désassemble à $SNES (hex) LEN instructions (Ghidra)")
    p.add_argument("--save-project", metavar="DIR:NAME", help="sauvegarde un projet Ghidra")
    p.add_argument("--analyze", action="store_true", help="lance l'auto-analyse Ghidra")
    p.add_argument("--report", type=Path, help="écrit le rapport en markdown (sinon stdout)")
    args = p.parse_args()

    raw = args.rom.read_bytes()
    data, smc = strip_smc_header(raw)
    mapping = detect_mapping(data, args.map)
    hdr = parse_header(data, mapping)

    # par défaut : info + heuristiques si rien n'est demandé
    if not any([args.info, args.vectors, args.find_printers, args.find_tables,
                args.find_dma, args.entropy, args.find_decompressors, args.gfx,
                args.gfx_bin, args.disasm, args.save_project, args.analyze]):
        args.info = args.find_printers = args.find_tables = args.find_dma = True

    R = []
    def out(s=""):
        R.append(s)

    out(f"# Reverse SNES — {args.rom.name}")
    out(f"- taille : {len(data):,} o ({len(data)//1024} Ko){' (+ en-tête SMC)' if smc else ''}")
    out(f"- mapping détecté : **{mapping}**")
    if args.info:
        out(f"- titre : `{hdr['title']}`")
        out(f"- mapper 0x{hdr['mapper']:02X} | type 0x{hdr['rom_type']:02X} | "
            f"ROM {hdr['rom_kb']}Ko | RAM {hdr['ram_kb']}Ko | région 0x{hdr['region']:02X}")
        out(f"- checksum 0x{hdr['checksum']:04X} / complément 0x{hdr['complement']:04X} "
            f"({'OK' if (hdr['checksum'] ^ hdr['complement']) == 0xFFFF else 'incohérent'})")
        vs = "  ".join(f"{k}={fmt_snes(vectors_to_snes(hdr, mapping).get(k, v))}"
                       for k, v in hdr["vectors"].items() if k in ("RESET", "NMI", "IRQ"))
        out(f"- vecteurs : {vs}")

    if args.find_printers:
        c = find_string_printers(data, mapping)
        out(f"\n## Afficheurs de texte candidats ({len(c)})")
        out("| SNES | chargement | terminateur | branche |")
        out("|---|---|---|---|")
        for x in c[:40]:
            out(f"| {fmt_snes(x['snes'])} | {x['load']} | "
                f"#${x['term']:02X} | {x['branch']} |")

    if args.find_tables:
        c = find_pointer_tables(data, mapping)
        c.sort(key=lambda x: -x["entries"])
        out(f"\n## Tables de pointeurs candidates ({len(c)})")
        out("| SNES | pas | entrées |")
        out("|---|---|---|")
        for x in c[:40]:
            out(f"| {fmt_snes(x['snes'])} | {x['stride']} o | {x['entries']} |")

    if args.find_dma:
        c = find_vram_dma(data, mapping)
        out(f"\n## Écritures registres VRAM/DMA ({len(c)})")
        out("| SNES | registre |")
        out("|---|---|")
        for x in c[:40]:
            out(f"| {fmt_snes(x['snes'])} | {x['reg']} (${x['regaddr']:04X}) |")

    if args.entropy:
        c = entropy_regions(data)
        c.sort(key=lambda r: -r[1])
        out(f"\n## Régions à forte entropie ({len(c)}) — blobs compressés candidats")
        out("| SNES | taille | entropie |")
        out("|---|---|---|")
        for off, ln, H in c[:40]:
            out(f"| {fmt_snes(file_to_snes(off, mapping))} | {ln} o | {H:.2f} |")

    if args.find_decompressors:
        c = find_decompressors(data, mapping)
        out(f"\n## Décompresseurs candidats ({len(c)})")
        out("| SNES | décalages | ld/st ind. | fenêtre | type deviné |")
        out("|---|---|---|---|---|")
        for x in c[:30]:
            out(f"| {fmt_snes(x['snes'])} | {x['shifts']} | "
                f"{x['ind_load']}/{x['ind_store']} | "
                f"{'oui' if x['window_copy'] else 'non'} | {x['guess']} |")

    if args.gfx or args.gfx_bin:
        if args.gfx_bin:
            path, bpp, w = args.gfx_bin.split(",")
            blob = Path(path).read_bytes()
            default_out = Path(path).with_suffix(".png")
            label = path
        else:
            off_s, len_s, bpp, w = args.gfx.split(",")
            o = int(off_s, 16)
            blob = data[o:o + int(len_s, 16)]
            default_out = args.rom.with_name(f"{args.rom.stem}_gfx_{off_s}.png")
            label = f"ROM @0x{o:06X}"
        img = render_tiles(blob, bpp=bpp, per_row=int(w))
        outp = args.out or default_out
        img.save(outp)
        out(f"\n## Graphismes rendus")
        out(f"- source : {label} ({len(blob)} o, {bpp}bpp, {w} tuiles/ligne)")
        out(f"- image  : `{outp}`")

    need_ghidra = args.vectors or args.disasm or args.save_project or args.analyze
    if need_ghidra:
        _start_ghidra()
        prog, api, consumer = build_program(data, mapping, args.rom.stem)
        try:
            pts = vectors_to_snes(hdr, mapping)
            if args.vectors or args.save_project:
                label_and_disassemble(prog, api, pts)
            if args.analyze:
                analyze(prog)
            if args.vectors:
                for name, snes in pts.items():
                    out(f"\n## {name} @ {fmt_snes(snes)}")
                    out("```")
                    R.extend(disasm_text(prog, api, snes, 30))
                    out("```")
            for spec in args.disasm:
                s, _, ln = spec.partition(",")
                snes = int(s, 16)
                out(f"\n## disasm @ {fmt_snes(snes)}")
                out("```")
                R.extend(disasm_text(prog, api, snes, int(ln or 30)))
                out("```")
            if args.save_project:
                d, _, nm = args.save_project.partition(":")
                save_project(prog, d, nm or args.rom.stem)
                out(f"\n_Projet Ghidra sauvegardé : {d}/{nm or args.rom.stem}_")
        finally:
            prog.release(consumer)

    text = "\n".join(R)
    if args.report:
        args.report.write_text(text, encoding="utf-8")
        print(f"Rapport écrit : {args.report}")
    else:
        print(text)


if __name__ == "__main__":
    main()
