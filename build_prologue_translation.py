#!/usr/bin/env python3
"""
Table-driven reinsertion of the Nage Libre prologue translations.

Principle (see docs/prologue_text_routines.md):
  - The prologue decompresses ALL of its script to $7F:64C0 (via $80:F8D8).
  - Each text line is a string of 16-bit IDs at $7F:64C0 + offset.
  - We hook $83:80FF (right after decompression) and, for each translated
    line, rewrite the English string at its offset, without touching
    hard-coded tilemap positions.

Data: docs/prologue_translation.csv  (columns offset_hex, n_ids, slot_words,
jp_decoded, en). Only the lines whose `en` column is filled in are reinserted.
The encoded length must fit in slot_words (otherwise an explicit error).

Output: nl-prologue-en.sfc
"""
import csv
import struct
from pathlib import Path

from patch_prologue_v3 import (
    JP_SPACE,
    ScatterAllocator,
    char_id_to_rom,
    encode_en,
    encode_to_slots,
    find_safe_ids,
    fix_checksum,
    make_pair_tile,
)

ROOT = Path(__file__).parent
ROM_PATH = ROOT / "Nage Libre - Seijaku no Suishin (Japan).sfc"
OUT_PATH = ROOT / "nl-prologue-en.sfc"
CSV_PATH = ROOT / "docs" / "prologue_translation.csv"

HOOK_POINT = 0x0180FF          # ROM offset de $83:80FF
HOOK_BANK = 0x83
HOOK_ADDR = 0xF8E3             # free area in bank $83
HOOK_ROM = 0x01F8E3           # ROM offset de $83:F8E3
FREE_END = 0x01FFE0           # keep a margin before the vectors
MIN_FONT_ID = 0x0100
WRAM_TILEMAP = 0x7F64C0

PRECOMBAT_CSV = ROOT / "docs" / "precombat_translation.csv"

# Scene guards: (offset_delta_from_$64C0, expected_ID_value) × 2.
# The $7F:64C0 buffer is shared by every decompressed scene; we only
# inject a scene if ITS signature (2 PRISTINE Japanese IDs at fixed
# offsets) is present. The guard is read BEFORE any write → stable.
#   Opening prologue: script offset refs $64C8(=+0x08)==$0124, $64D4==$0162.
#   Pre-battle (Stage 1 vs Tomomi): opcode header (precombat_buffer dump):
#     +0x08==$0212  AND  +0x60==$011C (operand of the 問答無用 line). These words
#     are in the header (never written by the injection) → stable signature.
GUARD_PROLOGUE = [(0x08, 0x0124), (0x14, 0x0162)]
GUARD_PRECOMBAT = [(0x08, 0x0212), (0x60, 0x011C)]


def safe_pair_ids(rom):
    return [cid for cid in find_safe_ids(rom) if cid >= MIN_FONT_ID]


def _load_csv(path):
    rows = []
    with path.open(encoding="utf-8") as f:
        for r in csv.DictReader(f):
            en = (r.get("en") or "").strip()
            if not en:
                continue
            rows.append({
                "offset": int(r["offset_hex"], 16),
                "slot": int(r["slot_words"]),
                "en": en,
            })
    return rows


def load_lines():
    """Compat: prologue lines only."""
    return _load_csv(CSV_PATH)


def load_scene_prologue():
    return {"name": "prologue", "guards": GUARD_PROLOGUE, "records": _load_csv(CSV_PATH)}


def load_scene_precombat():
    return {"name": "precombat", "guards": GUARD_PRECOMBAT,
            "records": _load_csv(PRECOMBAT_CSV)}


def assemble_hook(scenes, sections, table_snes):
    """MULTI-SCENE hook: JSL F8D8 then, for each scene (in order),
    checks its double guard; at the 1st scene that matches, copies its
    {offset,count,ids} records from the ROM table (bank $83) to
    $7F:64C0+offset, then RTL. A/X/Y 16-bit.

    Each block = the proven prologue injection logic + 2 guards;
    when a guard fails, we jump (BNE) to the next scene block.
    """
    TBL = 0x830000  # base for LDA.l TABLE,X (X = 16-bit address within bank $83)
    c = bytearray()
    c += bytes([0x22, 0xD8, 0xF8, 0x80])          # JSL $80F8D8 (original decompression)
    c += bytes([0x08, 0x8B])                       # PHP PHB
    c += bytes([0xC2, 0x30])                       # REP #$30  (A/X/Y 16-bit)
    c += bytes([0x48, 0xDA, 0x5A])                 # PHA PHX PHY
    c += bytes([0xA5, 0x0C, 0x48])                 # LDA $0C ; PHA  (sauve scratch $0C)
    c += bytes([0xE2, 0x20, 0xA9, 0x7F, 0x85, 0x0B, 0xC2, 0x20])  # bank de [$09] = $7F (1 fois)

    done_jmps = []                                 # JMP done operands to fix up
    for i, sc in enumerate(scenes):
        (g1o, g1v), (g2o, g2v) = sc["guards"]
        a1 = 0x64C0 + g1o
        c += bytes([0xAF, a1 & 0xFF, (a1 >> 8) & 0xFF, 0x7F])  # LDA.l $7F:a1
        c += bytes([0xC9, g1v & 0xFF, g1v >> 8])               # CMP #g1v
        bne1 = len(c); c += bytes([0xD0, 0x00])               # BNE next_scene
        a2 = 0x64C0 + g2o
        c += bytes([0xAF, a2 & 0xFF, (a2 >> 8) & 0xFF, 0x7F])  # LDA.l $7F:a2
        c += bytes([0xC9, g2v & 0xFF, g2v >> 8])               # CMP #g2v
        bne2 = len(c); c += bytes([0xD0, 0x00])               # BNE next_scene
        # guards satisfied → inject section i
        tsec = (table_snes + sections[i]) & 0xFFFF
        c += bytes([0xA2, tsec & 0xFF, (tsec >> 8) & 0xFF])    # LDX #section16
        rec = len(c)
        c += bytes([0xBF, TBL & 0xFF, (TBL >> 8) & 0xFF, (TBL >> 16) & 0xFF])  # LDA.l TBL,X (offset)
        c += bytes([0xC9, 0xFF, 0xFF])             # CMP #$FFFF (end of section)
        c += bytes([0xD0, 0x03])                   # BNE +3
        done_jmps.append(len(c)); c += bytes([0x4C, 0x00, 0x00])  # JMP done
        c += bytes([0x18, 0x69, 0xC0, 0x64])       # CLC ADC #$64C0
        c += bytes([0x85, 0x09])                   # STA $09 (dest lo16; $0B already $7F)
        c += bytes([0xE8, 0xE8])                   # INX INX → count
        c += bytes([0xBF, TBL & 0xFF, (TBL >> 8) & 0xFF, (TBL >> 16) & 0xFF])  # LDA.l TBL,X (count)
        c += bytes([0x0A, 0x85, 0x0C])             # ASL A ; STA $0C (length in bytes)
        c += bytes([0xE8, 0xE8])                   # INX INX → 1er id
        c += bytes([0xA0, 0x00, 0x00])             # LDY #$0000
        cpy = len(c)
        c += bytes([0xBF, TBL & 0xFF, (TBL >> 8) & 0xFF, (TBL >> 16) & 0xFF])  # LDA.l TBL,X (id)
        c += bytes([0x97, 0x09])                   # STA [$09],Y
        c += bytes([0xE8, 0xE8, 0xC8, 0xC8])       # INX INX ; INY INY
        c += bytes([0xC4, 0x0C])                   # CPY $0C
        bcc = len(c); c += bytes([0x90, 0x00])     # BCC cpy
        c[bcc + 1] = (cpy - (bcc + 2)) & 0xFF
        bra = len(c); c += bytes([0x80, 0x00])     # BRA rec
        c[bra + 1] = (rec - (bra + 2)) & 0xFF
        nxt = len(c)                               # BNE target (next scene)
        c[bne1 + 1] = (nxt - (bne1 + 2)) & 0xFF
        c[bne2 + 1] = (nxt - (bne2 + 2)) & 0xFF

    done = len(c)
    done_snes = HOOK_ADDR + done
    for j in done_jmps:
        c[j + 1] = done_snes & 0xFF
        c[j + 2] = (done_snes >> 8) & 0xFF
    c += bytes([0x68, 0x85, 0x0C])                 # PLA ; STA $0C (restaure scratch)
    c += bytes([0x7A, 0xFA, 0x68])                 # PLY PLX PLA
    c += bytes([0xAB, 0x28, 0x6B])                 # PLB PLP RTL
    return bytes(c)


def build_table(scenes, alloc):
    """Multi-scene ROM table. For each scene, one section:
        [ (offset, count, ids…) × n ,  $FFFF ]
    `sections[i]` = offset (from the start of the table) of scene i's section.
    Returns (table_bytes, sections, encoded_per_scene)."""
    tbl = bytearray()
    sections = []
    encoded_all = []
    for sc in scenes:
        sections.append(len(tbl))
        enc = []
        for r in sc["records"]:
            ids = encode_en(r["en"], alloc)
            while len(ids) > 1 and ids[-1] == JP_SPACE:
                ids.pop()
            if len(ids) > r["slot"]:
                raise SystemExit(
                    f"[{sc['name']}] @+{r['offset']:04X} : '{r['en']}' = "
                    f"{len(ids)} words > slot {r['slot']}")
            # $FFFF terminator: the engine stops there → no leftover Japanese.
            ids = ids + [0xFFFF]
            enc.append((r["offset"], ids))
            tbl += struct.pack("<HH", r["offset"], len(ids))
            for cid in ids:
                tbl += struct.pack("<H", cid)
        tbl += struct.pack("<H", 0xFFFF)  # end of section
        encoded_all.append(enc)
    return bytes(tbl), sections, encoded_all


def main():
    if not ROM_PATH.is_file():
        raise SystemExit(f"ROM not found: {ROM_PATH}")
    rom = bytearray(ROM_PATH.read_bytes())
    if rom[HOOK_POINT:HOOK_POINT + 4] != bytes([0x22, 0xD8, 0xF8, 0x80]):
        raise SystemExit("Point de hook $83:80FF inattendu — ROM JP propre ?")

    scenes = [load_scene_prologue()]
    if not scenes[0]["records"]:
        raise SystemExit("No 'en' line filled in docs/prologue_translation.csv")

    alloc = ScatterAllocator(safe_pair_ids(rom))

    # 1) table + encoding
    table, sections, encoded_all = build_table(scenes, alloc)

    # 2) hook (placed before the table)
    #   assembled once to know its size, then the table goes right after it.
    hook_tmp = assemble_hook(scenes, sections, 0x0000)
    table_snes = HOOK_ADDR + len(hook_tmp)
    hook = assemble_hook(scenes, sections, table_snes)
    assert len(hook) == len(hook_tmp)

    total = len(hook) + len(table)
    if HOOK_ROM + total > FREE_END:
        raise SystemExit(f"Bank $83 free area overflow: {total} bytes "
                         f"(available {FREE_END - HOOK_ROM} bytes). Shorten the translations.")

    # 3) glyphs of the pairs used
    for (cl, cr), cid in alloc.p2id.items():
        rom[char_id_to_rom(cid):char_id_to_rom(cid) + 64] = make_pair_tile(cl, cr)

    # 4) write hook + table, redirect $83:80FF
    rom[HOOK_ROM:HOOK_ROM + len(hook)] = hook
    tbl_rom = HOOK_ROM + len(hook)
    rom[tbl_rom:tbl_rom + len(table)] = table
    rom[HOOK_POINT:HOOK_POINT + 4] = bytes([0x22, HOOK_ADDR & 0xFF, (HOOK_ADDR >> 8) & 0xFF, HOOK_BANK])

    fix_checksum(rom)
    OUT_PATH.write_bytes(rom)

    n_lines = sum(len(e) for e in encoded_all)
    print(f"Written: {OUT_PATH.name}")
    print(f"  {n_lines} line(s) reinserted, {alloc.count()} font pairs")
    print(f"  hook {len(hook)} bytes @ $83:{HOOK_ADDR:04X}, table {len(table)} bytes @ $83:{table_snes:04X}")
    print(f"  area used: {total}/{FREE_END - HOOK_ROM} bytes")
    for enc in encoded_all:
        for off, ids in enc:
            print(f"    @+{off:04X}: {len(ids)} words")


if __name__ == "__main__":
    main()
