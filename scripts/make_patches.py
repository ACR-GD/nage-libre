#!/usr/bin/env python3
"""
Creates the release patches (BPS + IPS) between the Japanese ROM and nl-full-en.sfc,
then re-applies them to check that they reproduce the English ROM exactly.

usage: python3 scripts/make_patches.py OUT_DIR [BASE_NAME]
"""
import hashlib
import struct
import sys
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "Nage Libre - Seijaku no Suishin (Japan).sfc"
DST = ROOT / "nl-full-en.sfc"


def crc(b):
    return zlib.crc32(b) & 0xFFFFFFFF


# ---------------------------------------------------------------- BPS
def _num(n):
    out = bytearray()
    while True:
        x = n & 0x7F
        n >>= 7
        if n == 0:
            out.append(0x80 | x)
            return bytes(out)
        out.append(x)
        n -= 1


def make_bps(src, dst, meta=b""):
    """Linear BPS patch: SourceRead where target = source (runs >= 4), TargetRead elsewhere."""
    out = bytearray(b"BPS1") + _num(len(src)) + _num(len(dst)) + _num(len(meta)) + meta
    i, n = 0, len(dst)
    same = lambda k: k < len(src) and src[k] == dst[k]
    while i < n:
        j = i
        while j < n and same(j):
            j += 1
        if j - i >= 4 or (j == n and j > i):
            out += _num(((j - i - 1) << 2) | 0)
            i = j
            continue
        j = i
        while j < n:                    # TargetRead up to the next identical run >= 4
            if same(j) and all(same(k) for k in range(j, min(j + 4, n))) and min(j + 4, n) - j >= 4:
                break
            j += 1
        out += _num(((j - i - 1) << 2) | 1) + dst[i:j]
        i = j
    out += struct.pack("<II", crc(src), crc(dst))
    out += struct.pack("<I", crc(out))
    return bytes(out)


def apply_bps(src, patch):
    assert patch[:4] == b"BPS1"
    p = 4

    def num():
        nonlocal p
        data, shift = 0, 1
        while True:
            x = patch[p]; p += 1
            data += (x & 0x7F) * shift
            if x & 0x80:
                return data
            shift <<= 7
            data += shift

    ssz, tsz, msz = num(), num(), num()
    p += msz
    out = bytearray()
    sro = tro = 0
    end = len(patch) - 12
    while p < end:
        d = num(); mode, ln = d & 3, (d >> 2) + 1
        if mode == 0:
            out += src[len(out):len(out) + ln]
        elif mode == 1:
            out += patch[p:p + ln]; p += ln
        elif mode == 2:
            o = num(); sro += (-1 if o & 1 else 1) * (o >> 1)
            out += src[sro:sro + ln]; sro += ln
        else:
            o = num(); tro += (-1 if o & 1 else 1) * (o >> 1)
            for _ in range(ln):
                out.append(out[tro]); tro += 1
    s_crc, t_crc, p_crc = struct.unpack("<III", patch[-12:])
    assert len(src) == ssz and crc(src) == s_crc, "unexpected source ROM"
    assert crc(patch[:-4]) == p_crc, "corrupt patch"
    assert len(out) == tsz and crc(out) == t_crc, "incorrect output"
    return bytes(out)


# ---------------------------------------------------------------- IPS
def make_ips(src, dst):
    out = bytearray(b"PATCH")
    i, n = 0, len(dst)
    while i < n:
        if i < len(src) and src[i] == dst[i]:
            i += 1
            continue
        j = i
        while j < n and j - i < 0xFFFF and not (j < len(src) and src[j:j + 6] == dst[j:j + 6] and j + 6 <= len(src)):
            j += 1
        if i == 0x454F46:               # "EOF": step back one byte
            i -= 1
        chunk = dst[i:j]
        if len(set(chunk)) == 1 and len(chunk) > 8:
            out += i.to_bytes(3, "big") + b"\x00\x00" + len(chunk).to_bytes(2, "big") + chunk[:1]
        else:
            out += i.to_bytes(3, "big") + len(chunk).to_bytes(2, "big") + chunk
        i = j
    out += b"EOF"
    if len(dst) < len(src):
        out += len(dst).to_bytes(3, "big")
    return bytes(out)


def apply_ips(src, patch):
    out = bytearray(src)
    p = 5
    while patch[p:p + 3] != b"EOF":
        off = int.from_bytes(patch[p:p + 3], "big"); ln = int.from_bytes(patch[p + 3:p + 5], "big"); p += 5
        if ln == 0:
            rl = int.from_bytes(patch[p:p + 2], "big"); data = patch[p + 2:p + 3] * rl; p += 3
        else:
            data = patch[p:p + ln]; p += ln
        if len(out) < off + len(data):
            out += b"\x00" * (off + len(data) - len(out))
        out[off:off + len(data)] = data
    return bytes(out)


def main():
    out_dir = Path(sys.argv[1]); out_dir.mkdir(parents=True, exist_ok=True)
    base = sys.argv[2] if len(sys.argv) > 2 else "Nage Libre - Seijaku no Suishin (English)"
    src, dst = SRC.read_bytes(), DST.read_bytes()
    bps, ips = make_bps(src, dst), make_ips(src, dst)
    assert apply_bps(src, bps) == dst, "BPS: verification failed"
    assert apply_ips(src, ips) == dst, "IPS: verification failed"
    (out_dir / f"{base}.bps").write_bytes(bps)
    (out_dir / f"{base}.ips").write_bytes(ips)
    for name, d in (("original", src), ("patched", dst)):
        print(f"{name:8s} {len(d):>8,} B  CRC32 {crc(d):08X}  MD5 {hashlib.md5(d).hexdigest()}  "
              f"SHA-1 {hashlib.sha1(d).hexdigest()}")
    print(f"BPS {len(bps):,} B, IPS {len(ips):,} B — re-applied and verified")


if __name__ == "__main__":
    main()
