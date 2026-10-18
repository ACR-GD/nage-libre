#!/usr/bin/env python3
"""Décompile un script de scène du prologue Nage Libre depuis un dump WRAM.

Le script vit dans le bloc décompressé en $7F:64C0 (pointeur $06/$07/$08).
L'interpréteur $83:8103 lit des opcodes 16-bit (0x01–0x42), terminateur $FFFF.
Ce script :
  1. dérive la table opcode→handler et la taille (octets consommés) de chaque opcode
     depuis la ROM (validée contre les deltas de $06 observés dans les dumps),
  2. parcourt le bloc et émet un listing annoté,
  3. extrait les chaînes de texte (offset → IDs 16-bit, fin $FFFF) et les décode
     via docs/kanji_font_index.csv.

Usage:
  python3 scripts/decompile_prologue_script.py [dump_dir]
  (défaut : premier dump *_PC_838103_* trouvé)
"""
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ROM = ROOT / "Nage Libre - Seijaku no Suishin (Japan).sfc"
rom = ROM.read_bytes()

import importlib.util
_spec = importlib.util.spec_from_file_location("d", ROOT / "scripts" / "disasm_text_routines.py")
_d = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(_d)
lorom = _d.lorom; base_op = _d.base_op; SIZES = _d.SIZES


def opcode_handlers():
    start = lorom(0x83, 0x8103); table = {}; i = start
    while i < lorom(0x83, 0x83E2):
        if rom[i] == 0xC9 and rom[i+2] == 0x00 and rom[i+3] == 0xD0 and rom[i+5] == 0x20:
            table[rom[i+1]] = rom[i+6] | (rom[i+7] << 8); i += 11
        else:
            i += 1
    return table


def handler_features(tgt):
    o = lorom(0x83, tgt); blob = rom[o:o+400]
    # Opcode « ligne de texte » : charge $09 = offset + $64C0 (ADC #$64C0 / STA $09),
    # puis appelle un renderer de la famille $80:F4xx/F5xx (F4AB, F4CA, F5AC, …).
    textline = b"\x69\xC0\x64\x85\x09" in blob
    return {
        "textline": textline,
        "ptr": b"\x69\xC0\x64" in blob,
        "decomp": b"\x22\x63\xFA\x80" in blob,
        # rendu de texte ROM (pointeur fixe en banque 80/83/87) via la famille F4A7/F5xx
        "rom_text": (b"\x22\xA7\xF4\x80" in blob) and not textline,
    }


def opcode_size(tgt, depth=0, seen=None, mflag=0, xflag=0):
    """Octets consommés sur $06 = nb d'INC $06, en suivant les JSR internes (banque 83)."""
    if seen is None:
        seen = set()
    if depth > 4 or tgt in seen:
        return 0
    seen.add(tgt)
    off = lorom(0x83, tgt); incs = 0
    for _ in range(400):
        b = rom[off]; name, mode = base_op(b)
        if mode == "imm_m":
            sz = 3 if mflag == 0 else 2
        elif mode == "imm_x":
            sz = 3 if xflag == 0 else 2
        else:
            sz = SIZES.get(mode, 1)
        if b == 0xE6 and rom[off+1] == 0x06:
            incs += 1
        if b == 0x20:
            incs += opcode_size(rom[off+1] | (rom[off+2] << 8), depth+1, seen, mflag, xflag)
        if b == 0xC2:
            if rom[off+1] & 0x20: mflag = 0
            if rom[off+1] & 0x10: xflag = 0
        elif b == 0xE2:
            if rom[off+1] & 0x20: mflag = 1
            if rom[off+1] & 0x10: xflag = 1
        if name in ("RTS", "RTL"):
            break
        off += sz
    return incs


def load_font_map():
    m = {}
    p = ROOT / "docs" / "kanji_font_index.csv"
    if p.exists():
        for r in csv.DictReader(p.open()):
            try:
                m[int(r["char_id_hex"], 16)] = r.get("unicode_char", "") or ""
            except (ValueError, KeyError):
                pass
    return m


def find_dump():
    if len(sys.argv) > 1 and sys.argv[1] not in ("csv", "opcodes"):
        return Path(sys.argv[1])
    cands = sorted((ROOT / "mesen_dumps").glob("*_PC_838103_*"))
    if not cands:
        sys.exit("Aucun dump *_PC_838103_* trouvé.")
    return cands[0]


def main():
    dump = find_dump()
    binf = dump / "wram_7E0000_20000.bin"
    if not binf.exists():
        sys.exit(f"Dump WRAM introuvable : {binf}")
    w = binf.read_bytes()
    BASE = 0x10000 + 0x64C0  # $7F:64C0 dans le fichier $7E0000+0x20000

    def word(off):
        return w[BASE + off] | (w[BASE + off + 1] << 8)

    handlers = opcode_handlers()
    sizes = {k: opcode_size(v) for k, v in handlers.items()}
    feats = {k: handler_features(v) for k, v in handlers.items()}
    fmap = load_font_map()

    def decode_str(off, maxw=48):
        ids = []; o = off; terminated = False
        for _ in range(maxw):
            v = word(o)
            if v == 0xFFFF:
                terminated = True
                break
            ids.append(v); o += 2
        txt = "".join(fmap.get(v, "□") if v != 0x03FE else " " for v in ids)
        return ids, txt, terminated

    print(f"# Décompilation du script $7F:64C0  (dump : {dump.name})\n")
    pos = 0
    strings = []
    for _ in range(400):
        opc = word(pos)
        if opc == 0xFFFF:
            print(f"+{pos:04X}  FFFF              ── FIN DE SCÈNE ──")
            break
        if opc not in handlers:
            print(f"+{pos:04X}  {opc:04X}  ?? opcode inconnu — arrêt")
            break
        size = sizes.get(opc, 0) or 2
        nopr = (size - 2) // 2
        opr = [word(pos + 2 + 2*j) for j in range(nopr)]
        ft = feats[opc]
        # Un opcode « ligne de texte » résout réellement une chaîne si son 1er opérande
        # est un offset plausible (>= 0x100, au-delà du code) vers une chaîne terminée $FFFF.
        is_text = False
        soff = ids = txt = None
        if ft["textline"] and nopr >= 1 and opr[0] >= 0x100:
            soff = opr[0]
            ids, txt, term = decode_str(soff)
            if term and ids:
                is_text = True
        kind = []
        if is_text:
            kind.append("TEXTE")
        elif ft["textline"]:
            kind.append("data-ptr")  # même addressing $09=+64C0 mais table de données
        elif ft["rom_text"]:
            kind.append("texte-ROM")
        if ft["decomp"]:
            kind.append("DECOMP")
        if ft["ptr"] and not ft["textline"]:
            kind.append("ptr")
        tag = "/".join(kind) if kind else "ctrl"
        oprs = " ".join(f"{o:04X}" for o in opr)
        line = f"+{pos:04X}  op {opc:02X} [{size}o] {tag:12s} {oprs}"
        if is_text:
            line += f"   → @+{soff:04X} ({len(ids)} IDs) : «{txt}»"
            strings.append((pos, soff, ids, txt))
        print(line)
        pos += size

    print(f"\n## {len(strings)} chaîne(s) de texte référencée(s) :")
    for spos, soff, ids, txt in strings:
        print(f"  opcode @+{spos:04X} → +{soff:04X} : «{txt}»")
        print(f"      IDs: {' '.join(f'{v:03X}' for v in ids)}")

    return strings, word


def export_csv(out_path):
    """Génère une table de traduction : offset, slot (mots dispo), JP décodé, EN à remplir.
    Le slot = écart jusqu'à la chaîne suivante (par offset croissant) − 1 (terminateur)."""
    import io, contextlib
    with contextlib.redirect_stdout(io.StringIO()):
        strings, word = main()
    # offsets uniques des chaînes, triés
    offs = sorted({soff for _, soff, _, _ in strings})
    slot_of = {}
    for i, o in enumerate(offs):
        nxt = offs[i+1] if i+1 < len(offs) else o + 0x40
        slot_of[o] = (nxt - o) // 2 - 1  # mots utilisables (hors terminateur $FFFF)
    seen = set()
    rows = []
    for spos, soff, ids, txt in strings:
        if soff in seen:
            continue
        seen.add(soff)
        rows.append((soff, len(ids), slot_of[soff], txt))
    rows.sort()
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("offset_hex,n_ids,slot_words,jp_decoded,en\n")
        for soff, nids, slot, txt in rows:
            jp = txt.replace('"', "'")
            f.write(f"0x{soff:04X},{nids},{slot},\"{jp}\",\n")
    print(f"Écrit {out_path} ({len(rows)} lignes)")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "csv":
        out = sys.argv[2] if len(sys.argv) > 2 else str(ROOT / "docs" / "prologue_translation.csv")
        export_csv(out)
    else:
        main()
