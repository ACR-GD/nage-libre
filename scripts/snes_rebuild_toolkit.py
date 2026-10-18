#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
snes_rebuild_toolkit.py — Réinsertion / rebuild de ROM SNES (réutilisable)
===========================================================================

Complément de `snes_re_toolkit.py` (analyse). Ici on RECONSTRUIT une ROM SNES
après modifications (texte traduit, graphismes, code) « sans rien oublier » :

  * moteur d'écriture (offset FICHIER ou adresse SNES) avec SUIVI DES ÉCRITURES
    -> détection des CHEVAUCHEMENTS (deux patchs qui s'écrasent) ;
  * EXPANSION de la ROM (Mbit) + mise à jour de l'octet de taille du header ;
  * FIX CHECKSUM SNES (checksum + complément, avec miroir des tailles non
    puissances de deux) -> l'oubli n°1 qui fait planter/rejeter une ROM ;
  * recherche d'ESPACE LIBRE (runs de 0x00/0xFF) + ALLOCATEUR pour y placer des
    données étendues sans collision ;
  * REPOINTAGE de tables de pointeurs (2 ou 3 octets) ;
  * PATCHS IPS : génération (diff orig/modifiée) et application ;
  * VÉRIFICATION finale (header, checksum, taille, chevauchements) ;
  * MODE MANIFESTE : un build déclaratif (JSON) reproductible qui applique tout
    dans l'ordre (writes, repoints, expand, fix) -> « rebuild sans rien oublier ».

Tout est pilotable en ligne de commande ET importable comme bibliothèque
(`from snes_rebuild_toolkit import RomBuilder`).

Exemples
--------
    # expanser à 16 Mbit (2 Mo) et corriger header + checksum
    python3 scripts/snes_rebuild_toolkit.py jeu.sfc --expand 16 -o jeu_2mb.sfc

    # juste recalculer le checksum
    python3 scripts/snes_rebuild_toolkit.py jeu.sfc --fix-checksum -o jeu.sfc

    # lister l'espace libre (runs >= 256 o de 0x00/0xFF)
    python3 scripts/snes_rebuild_toolkit.py jeu.sfc --free-space --min 256

    # vérifier une ROM (checksum/header/taille)
    python3 scripts/snes_rebuild_toolkit.py jeu.sfc --verify

    # générer un patch IPS de diffusion (orig -> modifiée)
    python3 scripts/snes_rebuild_toolkit.py orig.sfc --make-ips modifiee.sfc -o patch.ips

    # appliquer un patch IPS
    python3 scripts/snes_rebuild_toolkit.py orig.sfc --apply-ips patch.ips -o patche.sfc

    # rebuild déclaratif complet depuis un manifeste
    python3 scripts/snes_rebuild_toolkit.py jeu.sfc --build build.json -o jeu_fr.sfc
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

# réutilise les helpers d'analyse (mapping, header, conversions)
sys.path.insert(0, str(Path(__file__).resolve().parent))
from snes_re_toolkit import (                       # noqa: E402
    strip_smc_header, detect_mapping, parse_header, header_base,
    snes_to_file, file_to_snes, fmt_snes,
)


# ===========================================================================
# Checksum / taille SNES
# ===========================================================================
def snes_checksum(data: bytes) -> int:
    """Checksum SNES 16 bits = somme de tous les octets, avec MIROIR de la partie
    excédentaire pour les tailles non puissances de deux (algorithme standard)."""
    size = len(data)
    if size == 0:
        return 0
    pow2 = 1 << (size.bit_length() - 1)             # plus grande puissance de 2 <= size
    if pow2 == size:
        return sum(data) & 0xFFFF
    base = sum(data[:pow2])
    rest = size - pow2
    rem = sum(data[pow2:])
    mult = pow2 // rest if rest else 0              # nb de répétitions pour combler
    return (base + rem * mult) & 0xFFFF


def rom_size_byte(size_bytes: int) -> int:
    """Octet $D7 du header : v tel que taille_Ko ≈ 2^v (arrondi au-dessus)."""
    kb = size_bytes // 1024
    v = 0
    while (1 << v) < kb:
        v += 1
    return v


# ===========================================================================
# IPS (génération / application)
# ===========================================================================
IPS_MAGIC = b"PATCH"
IPS_EOF = b"EOF"
IPS_EOF_OFF = 0x454F46                              # collision d'offset à éviter


def make_ips(orig: bytes, mod: bytes) -> bytes:
    """Diff IPS de `orig` -> `mod` (records simples, gère l'agrandissement)."""
    out = bytearray(IPS_MAGIC)
    i, n = 0, len(mod)
    while i < n:
        same = i < len(orig) and mod[i] == orig[i]
        if same:
            i += 1
            continue
        start = i
        while i < n and not (i < len(orig) and mod[i] == orig[i]):
            i += 1
            if i - start >= 0xFFFF:
                break
        if start == IPS_EOF_OFF:                    # évite l'offset "EOF"
            start -= 1
        chunk = mod[start:i]
        out += start.to_bytes(3, "big")
        out += len(chunk).to_bytes(2, "big")
        out += chunk
    out += IPS_EOF
    return bytes(out)


def apply_ips(rom: bytes, patch: bytes) -> bytes:
    if patch[:5] != IPS_MAGIC:
        raise ValueError("Patch IPS invalide (magic 'PATCH' absent)")
    data = bytearray(rom)
    i = 5
    while True:
        rec = patch[i:i + 3]
        if rec == IPS_EOF:
            break
        off = int.from_bytes(rec, "big"); i += 3
        size = int.from_bytes(patch[i:i + 2], "big"); i += 2
        if size == 0:                               # record RLE
            rl = int.from_bytes(patch[i:i + 2], "big"); i += 2
            b = patch[i]; i += 1
            if off + rl > len(data):
                data.extend(b"\x00" * (off + rl - len(data)))
            for k in range(rl):
                data[off + k] = b
        else:
            chunk = patch[i:i + size]; i += size
            if off + size > len(data):
                data.extend(b"\x00" * (off + size - len(data)))
            data[off:off + size] = chunk
    return bytes(data)


# ===========================================================================
# RomBuilder — moteur de réinsertion
# ===========================================================================
class RomBuilder:
    def __init__(self, path, mapping="auto"):
        raw = Path(path).read_bytes()
        body, self.had_smc = strip_smc_header(raw)
        self.data = bytearray(body)
        self.mapping = detect_mapping(self.data, mapping)
        self.writes = []                            # (start, end, tag)
        self.allocs = []                            # zones réservées par l'allocateur
        self._free = None                           # cache de la freelist

    # ---- lecture ----
    def read_file(self, off, n):
        return bytes(self.data[off:off + n])

    def read_snes(self, addr, n):
        fo = snes_to_file(addr, self.mapping)
        if fo is None:
            raise ValueError(f"Adresse SNES non mappable: {fmt_snes(addr)}")
        return self.read_file(fo, n)

    # ---- écriture (avec journalisation) ----
    def write_file(self, off, payload, tag=""):
        payload = bytes(payload)
        end = off + len(payload)
        if end > len(self.data):
            raise ValueError(f"Écriture hors ROM @0x{off:06X} (+{len(payload)}); "
                             f"taille={len(self.data)}. Expanser d'abord ?")
        self.data[off:end] = payload
        self.writes.append((off, end, tag))
        self._free = None
        return off

    def write_snes(self, addr, payload, tag=""):
        fo = snes_to_file(addr, self.mapping)
        if fo is None:
            raise ValueError(f"Adresse SNES non mappable: {fmt_snes(addr)}")
        return self.write_file(fo, payload, tag or fmt_snes(addr))

    def fill(self, off, length, byte=0x00, tag="fill"):
        self.write_file(off, bytes([byte & 0xFF]) * length, tag)

    # ---- expansion ----
    def expand_to(self, size_bytes, fill=0x00, fix_header=True):
        if size_bytes < len(self.data):
            raise ValueError("La taille cible est plus petite que la ROM actuelle.")
        if size_bytes % 0x8000:
            raise ValueError("La taille doit être un multiple de 0x8000 (32 Ko).")
        self.data.extend(bytes([fill & 0xFF]) * (size_bytes - len(self.data)))
        self._free = None
        if fix_header:
            self.fix_rom_size_byte()
        return len(self.data)

    def expand_mbit(self, mbit, **kw):
        return self.expand_to((mbit * 1024 * 1024) // 8, **kw)

    # ---- header ----
    def fix_rom_size_byte(self):
        b = header_base(self.mapping)
        if b + 0x17 < len(self.data):
            self.data[b + 0x17] = rom_size_byte(len(self.data))

    def fix_checksum(self):
        """Recalcule et écrit checksum + complément dans le header interne."""
        b = header_base(self.mapping)
        # état neutre : complément=0xFFFF, checksum=0x0000 (somme des 4 = 0x1FE,
        # constante quelle que soit la valeur finale -> calcul cohérent)
        self.data[b + 0x1C] = 0xFF
        self.data[b + 0x1D] = 0xFF
        self.data[b + 0x1E] = 0x00
        self.data[b + 0x1F] = 0x00
        chk = snes_checksum(self.data)
        cmp_ = chk ^ 0xFFFF
        self.data[b + 0x1C] = cmp_ & 0xFF
        self.data[b + 0x1D] = (cmp_ >> 8) & 0xFF
        self.data[b + 0x1E] = chk & 0xFF
        self.data[b + 0x1F] = (chk >> 8) & 0xFF
        return chk

    # ---- espace libre / allocateur ----
    def free_regions(self, min_run=0x40, fill_bytes=(0x00, 0xFF), start=0):
        """Runs >= min_run d'un même octet de remplissage. -> [(off, len, byte)]."""
        regions, n = [], len(self.data)
        i = start
        while i < n:
            b = self.data[i]
            if b in fill_bytes:
                j = i
                while j < n and self.data[j] == b:
                    j += 1
                if j - i >= min_run:
                    regions.append((i, j - i, b))
                i = j
            else:
                i += 1
        return regions

    def _ensure_free(self, min_run, fill_bytes):
        if self._free is None:
            self._free = self.free_regions(min_run, fill_bytes)
        return self._free

    def alloc(self, size, align=1, fill=0x00, min_run=None, fill_bytes=(0x00, 0xFF),
              tag="alloc"):
        """Réserve `size` octets dans une zone libre, en évitant les zones déjà
        allouées/écrites. Renvoie l'offset FICHIER. Lève si plus de place."""
        min_run = min_run or size
        for off, rlen, _b in self._ensure_free(min_run, fill_bytes):
            cur = off
            while cur + size <= off + rlen:
                if align > 1 and cur % align:
                    cur += align - (cur % align)
                    continue
                if not self._overlaps(cur, cur + size):
                    self.allocs.append((cur, cur + size, tag))
                    if fill:                        # réserve la zone (pré-remplie)
                        self.data[cur:cur + size] = bytes([fill & 0xFF]) * size
                    return cur                      # l'appelant écrit via write_file
                cur += 1
        raise RuntimeError(f"Pas d'espace libre contigu de {size} o (tag={tag}).")

    def _overlaps(self, s, e):
        for a, b, _ in self.allocs:
            if s < b and a < e:
                return True
        return False

    # ---- repointage ----
    def repoint(self, table_file_off, index, target_snes, width=2, tag="repoint"):
        """Écrit l'entrée `index` d'une table de pointeurs vers `target_snes`.
        width=2 -> 16 bits (intra-banque) ; width=3 -> pointeur long 24 bits."""
        off = table_file_off + index * width
        if width == 2:
            val = target_snes & 0xFFFF
            self.write_file(off, bytes([val & 0xFF, (val >> 8) & 0xFF]), tag)
        elif width == 3:
            self.write_file(off, bytes([target_snes & 0xFF,
                                        (target_snes >> 8) & 0xFF,
                                        (target_snes >> 16) & 0xFF]), tag)
        else:
            raise ValueError("width doit valoir 2 ou 3")
        return off

    def read_pointer(self, table_file_off, index, width=2, bank=None):
        off = table_file_off + index * width
        if width == 2:
            addr = self.data[off] | (self.data[off + 1] << 8)
            return ((bank or 0) << 16) | addr
        return self.data[off] | (self.data[off + 1] << 8) | (self.data[off + 2] << 16)

    # ---- vérification ----
    def overlaps(self):
        """Renvoie les paires d'écritures qui se chevauchent (potentiel oubli)."""
        ev = sorted(self.writes)
        bad = []
        for i in range(len(ev)):
            s1, e1, t1 = ev[i]
            for j in range(i + 1, len(ev)):
                s2, e2, t2 = ev[j]
                if s2 >= e1:
                    break
                if s1 < e2 and s2 < e1:
                    bad.append(((s1, e1, t1), (s2, e2, t2)))
        return bad

    def verify(self):
        b = header_base(self.mapping)
        stored = self.data[b + 0x1E] | (self.data[b + 0x1F] << 8)
        comp = snes_checksum(self.data)             # checksum « tel quel »
        return {
            "size": len(self.data),
            "size_pow2": (len(self.data) & (len(self.data) - 1)) == 0,
            "mult_32k": len(self.data) % 0x8000 == 0,
            "checksum_stored": stored,
            "checksum_calc": comp,
            "checksum_ok": stored == comp,
            "complement_ok": ((self.data[b + 0x1C] | (self.data[b + 0x1D] << 8))
                              == (stored ^ 0xFFFF)),
            "rom_size_byte": self.data[b + 0x17],
            "rom_size_byte_expected": rom_size_byte(len(self.data)),
            "overlaps": self.overlaps(),
        }

    # ---- sortie ----
    def save(self, path, keep_smc=False):
        out = bytes(self.data)
        if keep_smc and self.had_smc:
            out = b"\x00" * 0x200 + out
        Path(path).write_bytes(out)
        return len(out)


# ===========================================================================
# Manifeste de build déclaratif
# ===========================================================================
def _to_int(v):
    return v if isinstance(v, int) else int(str(v), 0)


def _payload_from_entry(e, base_dir):
    if "hex" in e:
        return bytes.fromhex(e["hex"].replace(" ", ""))
    if "bin" in e:
        p = Path(e["bin"])
        if not p.is_absolute():
            p = base_dir / p
        return p.read_bytes()
    if "fill" in e:
        return bytes([_to_int(e["fill"]) & 0xFF]) * _to_int(e["len"])
    raise ValueError(f"Entrée d'écriture sans 'hex'/'bin'/'fill': {e}")


def run_manifest(rb: RomBuilder, manifest: dict, base_dir: Path, log):
    if "expand_mbit" in manifest:
        rb.expand_mbit(_to_int(manifest["expand_mbit"]))
        log(f"- expand -> {len(rb.data):,} o ({_to_int(manifest['expand_mbit'])} Mbit)")
    elif "expand_bytes" in manifest:
        rb.expand_to(_to_int(manifest["expand_bytes"]))
        log(f"- expand -> {len(rb.data):,} o")

    for e in manifest.get("writes", []):
        payload = _payload_from_entry(e, base_dir)
        tag = e.get("tag", "")
        if "snes" in e:
            off = rb.write_snes(_to_int(e["snes"]), payload, tag)
        elif "file" in e:
            off = rb.write_file(_to_int(e["file"]), payload, tag)
        elif "alloc" in e:
            off = rb.alloc(len(payload), align=_to_int(e.get("align", 1)), tag=tag)
            rb.write_file(off, payload, tag)
        else:
            raise ValueError(f"Entrée d'écriture sans cible: {e}")
        log(f"- write {len(payload):>6} o @0x{off:06X} {('('+tag+')') if tag else ''}")

    for r in manifest.get("repoints", []):
        rb.repoint(_to_int(r["table_file"]), _to_int(r["index"]),
                   _to_int(r["target_snes"]), _to_int(r.get("width", 2)),
                   r.get("tag", "repoint"))
        log(f"- repoint table 0x{_to_int(r['table_file']):06X}[{_to_int(r['index'])}]"
            f" -> {fmt_snes(_to_int(r['target_snes']))}")

    if manifest.get("fix_rom_size", True):
        rb.fix_rom_size_byte()
    if manifest.get("fix_checksum", True):
        chk = rb.fix_checksum()
        log(f"- checksum corrigé : ${chk:04X}")


# ===========================================================================
# CLI
# ===========================================================================
def main():
    p = argparse.ArgumentParser(
        description="Boîte à outils de réinsertion / rebuild de ROM SNES.")
    p.add_argument("rom", type=Path)
    p.add_argument("--map", default="auto",
                   choices=["auto", "lorom", "hirom", "exhirom"])
    p.add_argument("-o", "--out", type=Path, help="ROM/patch de sortie")
    p.add_argument("--expand", type=int, metavar="MBIT",
                   help="expanse la ROM à MBIT Mbit + corrige header/checksum")
    p.add_argument("--fix-checksum", action="store_true",
                   help="recalcule checksum + complément")
    p.add_argument("--free-space", action="store_true",
                   help="liste les zones libres (runs de 0x00/0xFF)")
    p.add_argument("--min", type=int, default=256, help="taille mini d'un run libre")
    p.add_argument("--verify", action="store_true",
                   help="vérifie header/checksum/taille")
    p.add_argument("--make-ips", type=Path, metavar="MODIFIEE",
                   help="génère un patch IPS : rom(orig) -> MODIFIEE")
    p.add_argument("--apply-ips", type=Path, metavar="PATCH",
                   help="applique un patch IPS sur la rom")
    p.add_argument("--build", type=Path, metavar="MANIFEST.json",
                   help="rebuild déclaratif depuis un manifeste JSON")
    p.add_argument("--keep-smc", action="store_true",
                   help="ré-ajoute un en-tête SMC de 512 o à la sortie")
    args = p.parse_args()

    lines = []
    def log(s=""):
        print(s)
        lines.append(s)

    # --- patchs IPS (cas particuliers : pas de RomBuilder requis) ---
    if args.make_ips:
        orig, _ = strip_smc_header(args.rom.read_bytes())
        mod, _ = strip_smc_header(args.make_ips.read_bytes())
        patch = make_ips(orig, mod)
        outp = args.out or args.rom.with_suffix(".ips")
        outp.write_bytes(patch)
        log(f"Patch IPS écrit : {outp} ({len(patch):,} o)")
        return
    if args.apply_ips:
        rom, smc = strip_smc_header(args.rom.read_bytes())
        patched = apply_ips(rom, args.apply_ips.read_bytes())
        outp = args.out or args.rom.with_name(args.rom.stem + "_patched.sfc")
        outp.write_bytes(patched)
        log(f"ROM patchée : {outp} ({len(patched):,} o)")
        return

    rb = RomBuilder(args.rom, args.map)
    hdr = parse_header(rb.data, rb.mapping)
    log(f"# Rebuild SNES — {args.rom.name}")
    log(f"- titre : {hdr['title']!r}  | mapping : {rb.mapping}"
        f"  | taille : {len(rb.data):,} o")

    if args.free_space:
        regs = rb.free_regions(min_run=args.min)
        total = sum(r[1] for r in regs)
        log(f"\n## Espace libre (>= {args.min} o) — {len(regs)} zones, "
            f"{total:,} o au total")
        log("| SNES | fichier | taille | octet |")
        log("|---|---|---|---|")
        for off, ln, b in sorted(regs, key=lambda r: -r[1])[:40]:
            log(f"| {fmt_snes(file_to_snes(off, rb.mapping))} | 0x{off:06X} "
                f"| {ln:,} o | 0x{b:02X} |")

    if args.build:
        manifest = json.loads(args.build.read_text())
        if manifest.get("mapping") and manifest["mapping"] != "auto":
            rb.mapping = manifest["mapping"]
        log(f"\n## Manifeste {args.build.name}")
        run_manifest(rb, manifest, args.build.resolve().parent, log)

    if args.expand is not None:
        rb.expand_mbit(args.expand)
        rb.fix_checksum()
        log(f"\n- ROM expansée à {args.expand} Mbit ({len(rb.data):,} o), "
            f"header + checksum corrigés")
    elif args.fix_checksum:
        chk = rb.fix_checksum()
        log(f"\n- checksum recalculé : ${chk:04X}")

    if args.verify or args.build or args.expand is not None:
        v = rb.verify()
        log(f"\n## Vérification")
        log(f"- taille : {v['size']:,} o "
            f"(mult. 32 Ko: {'oui' if v['mult_32k'] else 'NON'}, "
            f"puiss. de 2: {'oui' if v['size_pow2'] else 'non'})")
        log(f"- checksum stocké ${v['checksum_stored']:04X} / "
            f"calculé ${v['checksum_calc']:04X} -> "
            f"{'OK' if v['checksum_ok'] else 'INCOHÉRENT'}")
        log(f"- complément : {'OK' if v['complement_ok'] else 'INCOHÉRENT'}")
        log(f"- octet taille header : 0x{v['rom_size_byte']:02X} "
            f"(attendu 0x{v['rom_size_byte_expected']:02X})")
        if v["overlaps"]:
            log(f"- ⚠️ {len(v['overlaps'])} CHEVAUCHEMENT(S) d'écriture :")
            for (a, b) in v["overlaps"][:10]:
                log(f"    0x{a[0]:06X}-0x{a[1]:06X} ({a[2]}) ∩ "
                    f"0x{b[0]:06X}-0x{b[1]:06X} ({b[2]})")
        else:
            log("- chevauchements : aucun")

    # --- sauvegarde si on a modifié quelque chose ---
    if args.out and (args.build or args.expand is not None or args.fix_checksum):
        n = rb.save(args.out, keep_smc=args.keep_smc)
        log(f"\nROM écrite : {args.out} ({n:,} o)")
    elif (args.build or args.expand is not None or args.fix_checksum) and not args.out:
        log("\n(aucun -o fourni : ROM non sauvegardée)")


if __name__ == "__main__":
    main()
