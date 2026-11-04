#!/usr/bin/env python3
"""Reusable PyGhidra toolkit for reverse-engineering Super Nintendo games
(65816) for translation (JP -> EN, EN -> FR).

Designed to be copied as-is into any SNES ROM-hacking project.
It combines:

  * Header analysis + automatic detection of the mapping (LoROM / HiROM /
    ExHiROM) and of a possible 512-byte SMC copier header.
  * SNES <-> file offset conversions in both directions.
  * HEURISTIC SCANNERS in pure Python (no Ghidra, so they're fast) that
    find the routines most useful for translation:
        - string printers  (loop: load through a pointer, compare to a
          terminator, branch)  -> where the text is rendered;
        - pointer tables    (2 or 3 bytes)                -> where the
          scripts / strings are;
        - DMA -> VRAM uploads    (writes to $2116/$2118 + $420B) -> where the font
          / tiles are loaded.
  * GRAPHICS: SNES tile decoding (2/4/8 bpp + Mode 7) and PNG rendering, to
    extract graphics that contain text (logos, title screens, labels).
  * COMPRESSION: entropy map (candidate compressed blobs) + heuristic
    detection of decompressors with a guessed type (RLE / LZSS / bit-packed /
    custom LZ). Full method: docs/snes_compression_id.en.md.
  * Ghidra integration (loaded on demand): correct per-bank memory map,
    vector setup (RESET/NMI/IRQ), disassembly at an address, and it can
    SAVE a Ghidra project you can open in the UI (labels for the routines found).

Examples:
    # info + vectors + heuristics, text report on standard output
    python3 scripts/snes_re_toolkit.py game.sfc

    # scanners only (no Ghidra needed), markdown report
    python3 scripts/snes_re_toolkit.py game.sfc --find-printers --find-tables \\
            --find-dma --report report.md

    # disassemble 40 instructions at $80:8000 and at $80:F8D8
    python3 scripts/snes_re_toolkit.py game.sfc --disasm 808000,40 --disasm 80F8D8,40

    # graphics + compression: render an area, list blobs and decompressors
    python3 scripts/snes_re_toolkit.py game.sfc --gfx 0x28000,0x2000,2,32 --out font.png
    python3 scripts/snes_re_toolkit.py game.sfc --entropy --find-decompressors --find-dma
    python3 scripts/snes_re_toolkit.py game.sfc --gfx-bin decompressed_dump.bin,4,16 --out dump.png

    # build + save a Ghidra project (can be opened in the GUI)
    python3 scripts/snes_re_toolkit.py game.sfc --save-project ./ghidra_proj:MyGame --analyze

Ghidra requirements (only for --vectors/--disasm/--save-project/--analyze):
    pip install pyghidra
    export GHIDRA_INSTALL_DIR=/path/to/ghidra   (otherwise the default value below)
"""
import argparse
import os
import struct
import sys
from pathlib import Path

os.environ.setdefault(
    "GHIDRA_INSTALL_DIR", "/opt/homebrew/Cellar/ghidra/12.1.1/libexec")

GHIDRA_LANG = "65816:LE:16:default"

# 65816 opcodes of interest for the scanners (indirect load through a pointer).
LOAD_VIA_PTR = {
    0xA7: "LDA [dp]",
    0xB7: "LDA [dp],Y",
    0xB2: "LDA (dp)",
    0xB1: "LDA (dp),Y",
    0xBF: "LDA addr_long,X",
    0xBD: "LDA addr,X",
    0xB9: "LDA addr,Y",
}
CMP_IMM = 0xC9            # CMP #imm  (terminator test)
BRANCHES = {0xF0: "BEQ", 0xD0: "BNE", 0x80: "BRA", 0x90: "BCC", 0xB0: "BCS"}


# ===========================================================================
# 1. ROM: copier header, mapping, internal header
# ===========================================================================
def strip_smc_header(data: bytes):
    """Removes the 512-byte SMC copier header if present. Returns (data, had_smc)."""
    if len(data) % 0x8000 == 0x200:
        return data[0x200:], True
    return data, False


def _score_header(data: bytes, base: int) -> int:
    """Plausibility score of a SNES internal header at offset `base`."""
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
    """Returns 'lorom' | 'hirom' | 'exhirom' (internal header at 0x7FC0/0xFFC0/0x40FFC0)."""
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


# ---- SNES <-> file conversions (depending on the mapping) ----
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
    if addr >= 0x8000:                      # mirror $80-$BF:8000-FFFF
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
# 2. Heuristic scanners (pure Python, no Ghidra needed)
# ===========================================================================
def find_string_printers(data: bytes, mapping: str, window: int = 24, limit: int = 60):
    """Finds text-printing loops: a load through a pointer followed,
    within a small window, by a CMP #imm (terminator) and a branch, the
    whole thing inside a loop (backward branch). Returns a list of candidates."""
    out = []
    n = len(data)
    for i in range(n - window):
        op = data[i]
        if op not in LOAD_VIA_PTR:
            continue
        seg = data[i:i + window]
        # look for CMP #imm
        jc = seg.find(bytes([CMP_IMM]))
        if jc < 2 or jc + 2 >= len(seg):
            continue
        term = seg[jc + 1]
        # branch right after the CMP (terminator)
        bpos = jc + 2
        if seg[bpos] not in BRANCHES:
            continue
        # a backward branch (loop) within the window
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
    """Detects 2-byte (within a bank) and 3-byte (long) pointer tables.
    A table = >= min_entries entries whose targets fall inside the ROM."""
    out = []
    n = len(data)
    rom_kb = max(8, n // 1024)

    def valid_addr(addr):
        return addr >= 0x8000 if mapping == "lorom" else True

    # --- 3 bytes (long pointers) ---
    i = 0
    while i < n - 3 * min_entries:
        cnt = 0
        j = i
        while j + 3 <= n:
            addr = data[j] | (data[j + 1] << 8)
            bank = data[j + 2]
            if addr in (0x0000, 0xFFFF):          # padding -> break
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

    # --- 2 bytes (within a bank); 0xFFFF/0x0000 break the run (padding) ---
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
    """Finds writes to the key registers of graphics uploads:
       STA $2116/$2117 (VRAM address), STA $4300.. (DMA params), STA $420B (go)."""
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
# 2b. Graphics: SNES tile decoding + PNG rendering
# ===========================================================================
# SNES planar formats (8x8): 2bpp=16 bytes, 4bpp=32 bytes, 8bpp=64 bytes; Mode 7=64 bytes
# linear (1 byte per pixel). Text "baked" into graphics (logos, "PUSH
# START", menu labels) -> to extract for translating/redrawing.
TILE_SIZE = {"2": 16, "4": 32, "8": 64, "m7": 64}


def _decode_planar(seg, bpp):
    """Returns 8x8 colour indexes for a planar tile (bpp = 2/4/8)."""
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
    """Renders `data` as a sheet of 8x8 tiles -> PIL image (greyscale
    by default, or `palette` = list of (r,g,b) indexed by colour)."""
    from PIL import Image
    size = TILE_SIZE[bpp]
    ntiles = len(data) // size
    if max_tiles:
        ntiles = min(ntiles, max_tiles)
    if ntiles == 0:
        raise SystemExit("Not enough data for one tile.")
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
# 2c. Compression: entropy (compressed blobs) + decompressor detection
# ===========================================================================
def entropy_regions(data, block=0x100, thresh=6.8):
    """HIGH-entropy regions (>= thresh bits/byte) = compressed or already
    dense data. A hint (not proof) of a compressed blob. Returns [(off,len,H)]."""
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


# Opcodes useful for detecting decompressors
SHIFT_OPS = {0x4A, 0x0A, 0x2A, 0x6A}          # LSR / ASL / ROL / ROR (on A)
IND_LOAD = {0xA7, 0xB7, 0xB1, 0xB2}           # LDA [dp]/[dp],Y/(dp),Y/(dp)
IND_STORE = {0x87, 0x97, 0x91, 0x92}          # STA …
BACK_BRANCH = {0x80, 0xD0, 0xF0, 0x90, 0xB0}  # BRA/BNE/BEQ/BCC/BCS (offset < 0)


def classify_decompressor(data, off, span=0x200):
    """Guesses the compression type from the structure of the code at `off`."""
    seg = data[off:off + span]
    nshift = sum(1 for b in seg if b in SHIFT_OPS)
    nload = sum(1 for b in seg if b in IND_LOAD)
    nstore = sum(1 for b in seg if b in IND_STORE)
    # LZ "window" copy: indexed read of a recently written buffer
    abs_copy = sum(1 for k in range(len(seg) - 3)
                   if seg[k] in (0xBD, 0xB9, 0xBF) and seg[k + 3] in (0x9D, 0x99, 0x9F))
    has_window = (nload and nstore) or abs_copy
    if nshift >= 4 and has_window:
        guess = "LZ + bit reader (LZSS/Nintendo-LZ or custom nibble/bit-based)"
    elif nshift >= 4:
        guess = "bit-level compression (Huffman/variable-length codes?)"
    elif has_window and nshift < 2:
        guess = "byte LZSS (back-reference, per-byte flags)"
    elif nstore >= 2 and nshift < 2 and not has_window:
        guess = "RLE (byte repetition)"
    else:
        guess = "undetermined (inspect in a disassembler)"
    return {"shifts": nshift, "ind_load": nload, "ind_store": nstore,
            "window_copy": has_window, "guess": guess}


def find_decompressors(data, mapping, window=0x60, min_shift=5, limit=40):
    """Finds routines that look like a decompressor: a cluster of shift
    operations (bit reader) + a "window" copy (LZ) + a backward loop.

    A NOISY and incomplete HEURISTIC: decompressors that use a JUMP TABLE
    (`JSR (table,X)`, like $80:F8D8 in Nage Libre) are split into
    subroutines and slip under the radar. For those, use the
    DMA->WRAM trace method (see docs/snes_compression_id.en.md)."""
    shift_pos = [k for k, b in enumerate(data) if b in SHIFT_OPS]
    sset = shift_pos
    out, seen = [], -window
    import bisect
    for s in shift_pos:
        if s - seen < window:                       # dedupe nearby clusters
            continue
        # number of shifts in [s, s+window)
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
# 3. Ghidra integration (imported on demand)
# ===========================================================================
def _start_ghidra():
    import pyghidra
    pyghidra.start()


def build_program(data: bytes, mapping: str, name: str):
    """Builds a 65816 ProgramDB and maps the ROM into it bank by bank according to the
    mapping. Returns (prog, api, consumer)."""
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
    """Disassembles and places a label (symbol) at each (label -> snes)."""
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
    """The vectors (RESET/NMI/IRQ) are 16-bit addresses in bank 0; in
    LoROM/HiROM the code lives in bank $80/$C0 -> we remap for disassembly."""
    bank = 0x80 if mapping == "lorom" else 0xC0
    pts = {}
    for name in ("RESET", "NMI", "IRQ"):
        v = hdr["vectors"][name]
        if v >= 0x8000:
            pts[name] = (bank << 16) | v
    return pts


def main():
    p = argparse.ArgumentParser(description="PyGhidra toolkit for SNES reverse engineering.")
    p.add_argument("rom", type=Path)
    p.add_argument("--map", default="auto", choices=["auto", "lorom", "hirom", "exhirom"])
    p.add_argument("--info", action="store_true", help="header + mapping")
    p.add_argument("--vectors", action="store_true", help="disassembles RESET/NMI/IRQ (Ghidra)")
    p.add_argument("--find-printers", action="store_true")
    p.add_argument("--find-tables", action="store_true")
    p.add_argument("--find-dma", action="store_true")
    p.add_argument("--entropy", action="store_true",
                   help="high-entropy regions (candidate compressed blobs)")
    p.add_argument("--find-decompressors", action="store_true",
                   help="routines that look like a decompressor + guessed type")
    p.add_argument("--gfx", metavar="OFF,LEN,BPP,W",
                   help="renders the ROM (hex FILE offset) as tiles -> PNG "
                        "(BPP=2/4/8/m7, W=tiles per row)")
    p.add_argument("--gfx-bin", metavar="PATH,BPP,W",
                   help="renders an external binary (e.g. a decompressed dump) as tiles")
    p.add_argument("--out", type=Path, default=None, help="output PNG path")
    p.add_argument("--disasm", action="append", default=[],
                   metavar="SNES,LEN", help="disassembles LEN instructions at $SNES (hex) (Ghidra)")
    p.add_argument("--save-project", metavar="DIR:NAME", help="saves a Ghidra project")
    p.add_argument("--analyze", action="store_true", help="runs Ghidra auto-analysis")
    p.add_argument("--report", type=Path, help="writes the report as markdown (otherwise stdout)")
    args = p.parse_args()

    raw = args.rom.read_bytes()
    data, smc = strip_smc_header(raw)
    mapping = detect_mapping(data, args.map)
    hdr = parse_header(data, mapping)

    # default: info + heuristics if nothing is requested
    if not any([args.info, args.vectors, args.find_printers, args.find_tables,
                args.find_dma, args.entropy, args.find_decompressors, args.gfx,
                args.gfx_bin, args.disasm, args.save_project, args.analyze]):
        args.info = args.find_printers = args.find_tables = args.find_dma = True

    R = []
    def out(s=""):
        R.append(s)

    out(f"# Reverse SNES — {args.rom.name}")
    out(f"- size: {len(data):,} bytes ({len(data)//1024} KB){' (+ SMC header)' if smc else ''}")
    out(f"- detected mapping: **{mapping}**")
    if args.info:
        out(f"- title: `{hdr['title']}`")
        out(f"- mapper 0x{hdr['mapper']:02X} | type 0x{hdr['rom_type']:02X} | "
            f"ROM {hdr['rom_kb']}KB | RAM {hdr['ram_kb']}KB | region 0x{hdr['region']:02X}")
        out(f"- checksum 0x{hdr['checksum']:04X} / complement 0x{hdr['complement']:04X} "
            f"({'OK' if (hdr['checksum'] ^ hdr['complement']) == 0xFFFF else 'inconsistent'})")
        vs = "  ".join(f"{k}={fmt_snes(vectors_to_snes(hdr, mapping).get(k, v))}"
                       for k, v in hdr["vectors"].items() if k in ("RESET", "NMI", "IRQ"))
        out(f"- vectors: {vs}")

    if args.find_printers:
        c = find_string_printers(data, mapping)
        out(f"\n## Candidate text printers ({len(c)})")
        out("| SNES | load | terminator | branch |")
        out("|---|---|---|---|")
        for x in c[:40]:
            out(f"| {fmt_snes(x['snes'])} | {x['load']} | "
                f"#${x['term']:02X} | {x['branch']} |")

    if args.find_tables:
        c = find_pointer_tables(data, mapping)
        c.sort(key=lambda x: -x["entries"])
        out(f"\n## Candidate pointer tables ({len(c)})")
        out("| SNES | stride | entries |")
        out("|---|---|---|")
        for x in c[:40]:
            out(f"| {fmt_snes(x['snes'])} | {x['stride']} bytes | {x['entries']} |")

    if args.find_dma:
        c = find_vram_dma(data, mapping)
        out(f"\n## VRAM/DMA register writes ({len(c)})")
        out("| SNES | register |")
        out("|---|---|")
        for x in c[:40]:
            out(f"| {fmt_snes(x['snes'])} | {x['reg']} (${x['regaddr']:04X}) |")

    if args.entropy:
        c = entropy_regions(data)
        c.sort(key=lambda r: -r[1])
        out(f"\n## High-entropy regions ({len(c)}) — candidate compressed blobs")
        out("| SNES | size | entropy |")
        out("|---|---|---|")
        for off, ln, H in c[:40]:
            out(f"| {fmt_snes(file_to_snes(off, mapping))} | {ln} bytes | {H:.2f} |")

    if args.find_decompressors:
        c = find_decompressors(data, mapping)
        out(f"\n## Candidate decompressors ({len(c)})")
        out("| SNES | shifts | ind. ld/st | window | guessed type |")
        out("|---|---|---|---|---|")
        for x in c[:30]:
            out(f"| {fmt_snes(x['snes'])} | {x['shifts']} | "
                f"{x['ind_load']}/{x['ind_store']} | "
                f"{'yes' if x['window_copy'] else 'no'} | {x['guess']} |")

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
        out(f"\n## Rendered graphics")
        out(f"- source: {label} ({len(blob)} bytes, {bpp}bpp, {w} tiles per row)")
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
                out(f"\n_Ghidra project saved: {d}/{nm or args.rom.stem}_")
        finally:
            prog.release(consumer)

    text = "\n".join(R)
    if args.report:
        args.report.write_text(text, encoding="utf-8")
        print(f"Report written: {args.report}")
    else:
        print(text)


if __name__ == "__main__":
    main()
