#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
snes_rebuild_toolkit.py — SNES ROM reinsertion / rebuild (reusable)
===========================================================================

Companion to `snes_re_toolkit.py` (analysis). This one REBUILDS a SNES ROM
after changes (translated text, graphics, code) "without forgetting anything":

  * write engine (FILE offset or SNES address) with WRITE TRACKING
    -> detects OVERLAPS (two patches overwriting each other);
  * ROM EXPANSION (Mbit) + update of the header size byte;
  * SNES CHECKSUM FIX (checksum + complement, with mirroring of
    non-power-of-two sizes) -> the number one thing people forget, which makes a ROM crash or get rejected;
  * FREE SPACE search (runs of 0x00/0xFF) + an ALLOCATOR to place
    expanded data there without collisions;
  * REPOINTING of pointer tables (2 or 3 bytes);
  * IPS PATCHES: generation (orig/modified diff) and application;
  * final VERIFICATION (header, checksum, size, overlaps);
  * MANIFEST MODE: a reproducible declarative (JSON) build that applies everything
    in order (writes, repoints, expand, fix) -> "rebuild without forgetting anything".

Everything can be driven from the command line AND imported as a library
(`from snes_rebuild_toolkit import RomBuilder`).

Examples
--------
    # expand to 16 Mbit (2 MB) and fix header + checksum
    python3 scripts/snes_rebuild_toolkit.py game.sfc --expand 16 -o game_2mb.sfc

    # just recompute the checksum
    python3 scripts/snes_rebuild_toolkit.py game.sfc --fix-checksum -o game.sfc

    # list the free space (runs >= 256 bytes of 0x00/0xFF)
    python3 scripts/snes_rebuild_toolkit.py game.sfc --free-space --min 256

    # verify a ROM (checksum/header/size)
    python3 scripts/snes_rebuild_toolkit.py game.sfc --verify

    # make a distribution IPS patch (orig -> modified)
    python3 scripts/snes_rebuild_toolkit.py orig.sfc --make-ips modified.sfc -o patch.ips

    # apply an IPS patch
    python3 scripts/snes_rebuild_toolkit.py orig.sfc --apply-ips patch.ips -o patched.sfc

    # full declarative rebuild from a manifest
    python3 scripts/snes_rebuild_toolkit.py game.sfc --build build.json -o game_en.sfc
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

# reuses the analysis helpers (mapping, header, conversions)
sys.path.insert(0, str(Path(__file__).resolve().parent))
from snes_re_toolkit import (                       # noqa: E402
    strip_smc_header, detect_mapping, parse_header, header_base,
    snes_to_file, file_to_snes, fmt_snes,
)


# ===========================================================================
# SNES checksum / size
# ===========================================================================
def snes_checksum(data: bytes) -> int:
    """16-bit SNES checksum = sum of all bytes, MIRRORING the excess part
    for non-power-of-two sizes (standard algorithm)."""
    size = len(data)
    if size == 0:
        return 0
    pow2 = 1 << (size.bit_length() - 1)             # largest power of 2 <= size
    if pow2 == size:
        return sum(data) & 0xFFFF
    base = sum(data[:pow2])
    rest = size - pow2
    rem = sum(data[pow2:])
    mult = pow2 // rest if rest else 0              # number of repeats needed to fill
    return (base + rem * mult) & 0xFFFF


def rom_size_byte(size_bytes: int) -> int:
    """Header byte $D7: v such that size_KB ≈ 2^v (rounded up)."""
    kb = size_bytes // 1024
    v = 0
    while (1 << v) < kb:
        v += 1
    return v


# ===========================================================================
# IPS (generation / application)
# ===========================================================================
IPS_MAGIC = b"PATCH"
IPS_EOF = b"EOF"
IPS_EOF_OFF = 0x454F46                              # offset collision to avoid


def make_ips(orig: bytes, mod: bytes) -> bytes:
    """IPS diff of `orig` -> `mod` (simple records, handles enlargement)."""
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
        if start == IPS_EOF_OFF:                    # avoid the "EOF" offset
            start -= 1
        chunk = mod[start:i]
        out += start.to_bytes(3, "big")
        out += len(chunk).to_bytes(2, "big")
        out += chunk
    out += IPS_EOF
    return bytes(out)


def apply_ips(rom: bytes, patch: bytes) -> bytes:
    if patch[:5] != IPS_MAGIC:
        raise ValueError("Invalid IPS patch ('PATCH' magic missing)")
    data = bytearray(rom)
    i = 5
    while True:
        rec = patch[i:i + 3]
        if rec == IPS_EOF:
            break
        off = int.from_bytes(rec, "big"); i += 3
        size = int.from_bytes(patch[i:i + 2], "big"); i += 2
        if size == 0:                               # RLE record
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
# RomBuilder — reinsertion engine
# ===========================================================================
class RomBuilder:
    def __init__(self, path, mapping="auto"):
        raw = Path(path).read_bytes()
        body, self.had_smc = strip_smc_header(raw)
        self.data = bytearray(body)
        self.mapping = detect_mapping(self.data, mapping)
        self.writes = []                            # (start, end, tag)
        self.allocs = []                            # areas reserved by the allocator
        self._free = None                           # free-list cache

    # ---- reading ----
    def read_file(self, off, n):
        return bytes(self.data[off:off + n])

    def read_snes(self, addr, n):
        fo = snes_to_file(addr, self.mapping)
        if fo is None:
            raise ValueError(f"Unmappable SNES address: {fmt_snes(addr)}")
        return self.read_file(fo, n)

    # ---- writing (with logging) ----
    def write_file(self, off, payload, tag=""):
        payload = bytes(payload)
        end = off + len(payload)
        if end > len(self.data):
            raise ValueError(f"Write outside the ROM @0x{off:06X} (+{len(payload)}); "
                             f"size={len(self.data)}. Expand first?")
        self.data[off:end] = payload
        self.writes.append((off, end, tag))
        self._free = None
        return off

    def write_snes(self, addr, payload, tag=""):
        fo = snes_to_file(addr, self.mapping)
        if fo is None:
            raise ValueError(f"Unmappable SNES address: {fmt_snes(addr)}")
        return self.write_file(fo, payload, tag or fmt_snes(addr))

    def fill(self, off, length, byte=0x00, tag="fill"):
        self.write_file(off, bytes([byte & 0xFF]) * length, tag)

    # ---- expansion ----
    def expand_to(self, size_bytes, fill=0x00, fix_header=True):
        if size_bytes < len(self.data):
            raise ValueError("The target size is smaller than the current ROM.")
        if size_bytes % 0x8000:
            raise ValueError("The size must be a multiple of 0x8000 (32 KB).")
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
        """Recomputes and writes checksum + complement into the internal header."""
        b = header_base(self.mapping)
        # neutral state: complement=0xFFFF, checksum=0x0000 (the sum of the 4 = 0x1FE,
        # constant whatever the final value -> consistent computation)
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

    # ---- free space / allocator ----
    def free_regions(self, min_run=0x40, fill_bytes=(0x00, 0xFF), start=0):
        """Runs >= min_run of the same fill byte. -> [(off, len, byte)]."""
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
        """Reserves `size` bytes in a free area, avoiding areas already
        allocated/written. Returns the FILE offset. Raises if there is no room left."""
        min_run = min_run or size
        for off, rlen, _b in self._ensure_free(min_run, fill_bytes):
            cur = off
            while cur + size <= off + rlen:
                if align > 1 and cur % align:
                    cur += align - (cur % align)
                    continue
                if not self._overlaps(cur, cur + size):
                    self.allocs.append((cur, cur + size, tag))
                    if fill:                        # reserve the area (pre-filled)
                        self.data[cur:cur + size] = bytes([fill & 0xFF]) * size
                    return cur                      # the caller writes via write_file
                cur += 1
        raise RuntimeError(f"No contiguous free space of {size} bytes (tag={tag}).")

    def _overlaps(self, s, e):
        for a, b, _ in self.allocs:
            if s < b and a < e:
                return True
        return False

    # ---- repointing ----
    def repoint(self, table_file_off, index, target_snes, width=2, tag="repoint"):
        """Writes entry `index` of a pointer table to point at `target_snes`.
        width=2 -> 16 bits (within the bank); width=3 -> 24-bit long pointer."""
        off = table_file_off + index * width
        if width == 2:
            val = target_snes & 0xFFFF
            self.write_file(off, bytes([val & 0xFF, (val >> 8) & 0xFF]), tag)
        elif width == 3:
            self.write_file(off, bytes([target_snes & 0xFF,
                                        (target_snes >> 8) & 0xFF,
                                        (target_snes >> 16) & 0xFF]), tag)
        else:
            raise ValueError("width must be 2 or 3")
        return off

    def read_pointer(self, table_file_off, index, width=2, bank=None):
        off = table_file_off + index * width
        if width == 2:
            addr = self.data[off] | (self.data[off + 1] << 8)
            return ((bank or 0) << 16) | addr
        return self.data[off] | (self.data[off + 1] << 8) | (self.data[off + 2] << 16)

    # ---- verification ----
    def overlaps(self):
        """Returns the pairs of writes that overlap (potential mistake)."""
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
        comp = snes_checksum(self.data)             # checksum "as is"
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

    # ---- output ----
    def save(self, path, keep_smc=False):
        out = bytes(self.data)
        if keep_smc and self.had_smc:
            out = b"\x00" * 0x200 + out
        Path(path).write_bytes(out)
        return len(out)


# ===========================================================================
# Declarative build manifest
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
    raise ValueError(f"Write entry without 'hex'/'bin'/'fill': {e}")


def run_manifest(rb: RomBuilder, manifest: dict, base_dir: Path, log):
    if "expand_mbit" in manifest:
        rb.expand_mbit(_to_int(manifest["expand_mbit"]))
        log(f"- expand -> {len(rb.data):,} bytes ({_to_int(manifest['expand_mbit'])} Mbit)")
    elif "expand_bytes" in manifest:
        rb.expand_to(_to_int(manifest["expand_bytes"]))
        log(f"- expand -> {len(rb.data):,} bytes")

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
            raise ValueError(f"Write entry without a target: {e}")
        log(f"- write {len(payload):>6} bytes @0x{off:06X} {('('+tag+')') if tag else ''}")

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
        log(f"- checksum fixed: ${chk:04X}")


# ===========================================================================
# CLI
# ===========================================================================
def main():
    p = argparse.ArgumentParser(
        description="SNES ROM reinsertion / rebuild toolkit.")
    p.add_argument("rom", type=Path)
    p.add_argument("--map", default="auto",
                   choices=["auto", "lorom", "hirom", "exhirom"])
    p.add_argument("-o", "--out", type=Path, help="output ROM/patch")
    p.add_argument("--expand", type=int, metavar="MBIT",
                   help="expands the ROM to MBIT Mbit + fixes header/checksum")
    p.add_argument("--fix-checksum", action="store_true",
                   help="recomputes checksum + complement")
    p.add_argument("--free-space", action="store_true",
                   help="lists the free areas (runs of 0x00/0xFF)")
    p.add_argument("--min", type=int, default=256, help="minimum size of a free run")
    p.add_argument("--verify", action="store_true",
                   help="verifies header/checksum/size")
    p.add_argument("--make-ips", type=Path, metavar="MODIFIED",
                   help="makes an IPS patch: rom(orig) -> MODIFIED")
    p.add_argument("--apply-ips", type=Path, metavar="PATCH",
                   help="applies an IPS patch to the rom")
    p.add_argument("--build", type=Path, metavar="MANIFEST.json",
                   help="declarative rebuild from a JSON manifest")
    p.add_argument("--keep-smc", action="store_true",
                   help="adds a 512-byte SMC header back to the output")
    args = p.parse_args()

    lines = []
    def log(s=""):
        print(s)
        lines.append(s)

    # --- IPS patches (special cases: no RomBuilder needed) ---
    if args.make_ips:
        orig, _ = strip_smc_header(args.rom.read_bytes())
        mod, _ = strip_smc_header(args.make_ips.read_bytes())
        patch = make_ips(orig, mod)
        outp = args.out or args.rom.with_suffix(".ips")
        outp.write_bytes(patch)
        log(f"IPS patch written: {outp} ({len(patch):,} bytes)")
        return
    if args.apply_ips:
        rom, smc = strip_smc_header(args.rom.read_bytes())
        patched = apply_ips(rom, args.apply_ips.read_bytes())
        outp = args.out or args.rom.with_name(args.rom.stem + "_patched.sfc")
        outp.write_bytes(patched)
        log(f"Patched ROM: {outp} ({len(patched):,} bytes)")
        return

    rb = RomBuilder(args.rom, args.map)
    hdr = parse_header(rb.data, rb.mapping)
    log(f"# Rebuild SNES — {args.rom.name}")
    log(f"- title: {hdr['title']!r}  | mapping: {rb.mapping}"
        f"  | size: {len(rb.data):,} bytes")

    if args.free_space:
        regs = rb.free_regions(min_run=args.min)
        total = sum(r[1] for r in regs)
        log(f"\n## Free space (>= {args.min} bytes) — {len(regs)} areas, "
            f"{total:,} bytes in total")
        log("| SNES | file | size | byte |")
        log("|---|---|---|---|")
        for off, ln, b in sorted(regs, key=lambda r: -r[1])[:40]:
            log(f"| {fmt_snes(file_to_snes(off, rb.mapping))} | 0x{off:06X} "
                f"| {ln:,} bytes | 0x{b:02X} |")

    if args.build:
        manifest = json.loads(args.build.read_text())
        if manifest.get("mapping") and manifest["mapping"] != "auto":
            rb.mapping = manifest["mapping"]
        log(f"\n## Manifest {args.build.name}")
        run_manifest(rb, manifest, args.build.resolve().parent, log)

    if args.expand is not None:
        rb.expand_mbit(args.expand)
        rb.fix_checksum()
        log(f"\n- ROM expanded to {args.expand} Mbit ({len(rb.data):,} bytes), "
            f"header + checksum fixed")
    elif args.fix_checksum:
        chk = rb.fix_checksum()
        log(f"\n- checksum recomputed: ${chk:04X}")

    if args.verify or args.build or args.expand is not None:
        v = rb.verify()
        log(f"\n## Verification")
        log(f"- size: {v['size']:,} bytes "
            f"(mult. of 32 KB: {'yes' if v['mult_32k'] else 'NO'}, "
            f"power of 2: {'yes' if v['size_pow2'] else 'no'})")
        log(f"- stored checksum ${v['checksum_stored']:04X} / "
            f"computed ${v['checksum_calc']:04X} -> "
            f"{'OK' if v['checksum_ok'] else 'INCONSISTENT'}")
        log(f"- complement: {'OK' if v['complement_ok'] else 'INCONSISTENT'}")
        log(f"- header size byte: 0x{v['rom_size_byte']:02X} "
            f"(expected 0x{v['rom_size_byte_expected']:02X})")
        if v["overlaps"]:
            log(f"- ⚠️ {len(v['overlaps'])} write OVERLAP(S):")
            for (a, b) in v["overlaps"][:10]:
                log(f"    0x{a[0]:06X}-0x{a[1]:06X} ({a[2]}) ∩ "
                    f"0x{b[0]:06X}-0x{b[1]:06X} ({b[2]})")
        else:
            log("- overlaps: none")

    # --- save if anything was changed ---
    if args.out and (args.build or args.expand is not None or args.fix_checksum):
        n = rb.save(args.out, keep_smc=args.keep_smc)
        log(f"\nROM written: {args.out} ({n:,} bytes)")
    elif (args.build or args.expand is not None or args.fix_checksum) and not args.out:
        log("\n(no -o given: ROM not saved)")


if __name__ == "__main__":
    main()
