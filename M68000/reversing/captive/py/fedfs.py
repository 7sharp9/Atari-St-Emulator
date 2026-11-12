#!/usr/bin/env python3
"""Captive's "fed1:" disk file system: track decode, directory, file extract, depack.

Usage (from M68000/):
  uv run python reversing/captive/py/fedfs.py <disk.st> list
  uv run python reversing/captive/py/fedfs.py <disk.st> extract <outdir>

Format (README "Disk format"). A unit is one physical track side, unit = 2*track + side. A unit
holds 1280 big-endian longs: a header long stored inverted (NOT), 1278 data longs each stored as
value + k1 with k1 starting at $eff478ed and advancing by $bffb7e5e per long, then a checksum long
making the 32-bit sum of header, decoded data and checksum zero. The keys are the loader's
(`$26a`/`$26e` in low RAM, read at `$8d0`/`$8d4`); the decode is its loop `$8cc-$90c`. A file
occupies `count` consecutive tracks on one side (units unit, unit+2, ...), 5112 data bytes each;
in the last unit the checksum sits right after the file's last long, so a full-track decode of it
fails the checksum while its data is right. The directory (20-byte entries: name[12], start unit
word, unit count byte, pad, length long) is in the volume block, unit 1 (`read_dir`).

Most files are packed with the game's own packer, magic "RNC\\x01" but not Rob Northen's format:
header magic, unpacked length, packed length, then the packed bytes, read backwards. `depack` is a
transcription of the game's depacker at runtime `$303c-$31c2` (in BootFile's code).
"""
import os
import struct
import sys

M = 0xFFFFFFFF
K1, K2 = 0xEFF478ED, 0xBFFB7E5E
UNIT_DATA = 1278 * 4


def decode_unit(img, unit, nlongs=1278):
    """Decode one unit; return (header, data bytes, checksum ok) over the first nlongs longs."""
    raw = img[unit * 5120:(unit + 1) * 5120]
    L = struct.unpack('>1280I', raw)
    hdr = (~L[0]) & M
    k1, s, out = K1, hdr, []
    for x in L[1:1 + nlongs]:
        v = (x - k1) & M
        k1 = (k1 + K2) & M
        s = (s + v) & M
        out.append(v)
    s = (s + L[1 + nlongs]) & M
    return hdr, struct.pack('>%dI' % nlongs, *out), s == 0


def read_dir(img, unit=1):
    """Unit 1 is the volume block: its header long is its length in longs ($15b), then
    `1ce2 0047`, the volume name "fed1", a 176-byte table (role unknown) and from byte 188 the
    directory."""
    hdr, _, _ = decode_unit(img, unit, 1)
    _, data, ok = decode_unit(img, unit, hdr)
    if not ok or data[4:8] != b'fed1' or not data[188:].startswith(b'fed_'):
        raise SystemExit('no volume block in unit %d' % unit)
    ents, i = [], 188
    while i + 20 <= len(data) and data[i]:
        e = data[i:i + 20]
        name = e[:12].split(b'\0')[0].decode('latin-1')
        u, count, _pad, length = struct.unpack('>HBBI', e[12:20])
        ents.append((name, u, count, length))
        i += 20
    return ents


def read_span(img, unit, count, nbytes):
    """The first nbytes of a file; returns (bytes, every unit's checksum ok)."""
    out, ok_all = b'', True
    for k in range(count):
        n = min(1278, (nbytes - len(out) + 3) // 4)
        if n <= 0:
            break
        _, data, ok = decode_unit(img, unit + 2 * k, n)
        out += data
        ok_all &= ok
    return out[:nbytes], ok_all


class _Bits:
    """The depacker's bit reader: `add.b D3,D3 / bne / move.b -(A6),D3 / roxl.b #1,D3`."""

    def __init__(self, src, end):
        self.src, self.p = src, end - 1
        self.d3 = src[self.p]

    def bit(self):
        c = self.d3 >> 7
        self.d3 = (self.d3 << 1) & 0xFF
        if self.d3:
            return c
        self.p -= 1
        b = self.src[self.p]
        self.d3 = ((b << 1) | c) & 0xFF
        return b >> 7

    def bits(self, n):
        v = 0
        for _ in range(n):
            v = (v << 1) | self.bit()
        return v


def depack(data):
    """Unpack a "RNC\\x01" file; raises ValueError on a malformed stream."""
    if data[:4] != b'RNC\x01':
        raise ValueError('no RNC magic')
    ulen, plen = struct.unpack('>II', data[4:12])
    src = data[12:12 + plen]
    if len(src) != plen:
        raise ValueError('short packed data')
    bs = _Bits(src, plen)
    out = bytearray(ulen)
    a3 = ulen                      # output is written backwards from the end

    def put(b):
        nonlocal a3
        if a3 <= 0:
            raise ValueError('output overrun')
        a3 -= 1
        out[a3] = b

    while True:
        # $30a6: literal run
        if bs.bit():
            if not bs.bit():
                n = 0
            else:
                d1 = 3
                while True:
                    width = (0x0A, 0x03, 0x02, 0x02)[d1]
                    n = bs.bits(width)
                    if d1 == 0 or n != (1 << width) - 1:
                        break
                    d1 -= 1
                n += (0x0E, 0x07, 0x04, 0x01)[d1]
            for _ in range(n + 1):
                bs.p -= 1
                if bs.p < 0:
                    raise ValueError('input underrun')
                put(src[bs.p])
        if bs.p <= 0:              # cmpa.l A4,A6 / ble: packed data used up
            break
        # $30fc: match length
        d0 = 3
        while d0 >= 0 and bs.bit():
            d0 -= 1
        k = d0 + 1
        length = bs.bits((0x0A, 0x02, 0x01, 0x00, 0x00)[k]) + (0x0A, 0x06, 0x04, 0x03, 0x02)[k]
        # $313a: match offset
        if length == 2:
            off = bs.bits(9) + 64 if bs.bit() else bs.bits(6)
        else:
            d0 = 1
            while d0 >= 0 and bs.bit():
                d0 -= 1
            k = d0 + 1
            off = bs.bits((0x0B, 0x04, 0x07)[k] + 1) + (0x0120, 0x0000, 0x0020)[k]
        # $307c: copy length bytes from A0 = A3 + off + length - 1 down (A3 + 1 when off is 0)
        a0 = a3 + off + length - 1 if off else a3 + 1
        for _ in range(length):
            a0 -= 1
            put(out[a0])
    if a3 != 0:
        raise ValueError('stream ended with %d bytes unwritten' % a3)
    return bytes(out)


def files(img):
    """Yield (name, unit, count, length, body, kind, checksums ok) for every directory entry."""
    for name, unit, count, length in read_dir(img):
        head, _ = read_span(img, unit, count, 12)
        if head[:4] == b'RNC\x01':
            nbytes = 12 + struct.unpack('>I', head[8:12])[0]
            raw, ok = read_span(img, unit, count, nbytes)
            yield name, unit, count, length, depack(raw), 'packed', ok
        else:
            raw, ok = read_span(img, unit, count, length)
            yield name, unit, count, length, raw, 'raw', ok


def main():
    img = open(sys.argv[1], 'rb').read()
    cmd = sys.argv[2] if len(sys.argv) > 2 else 'list'
    outdir = sys.argv[3] if cmd == 'extract' else None
    if outdir:
        os.makedirs(outdir, exist_ok=True)
    for name, unit, count, length, body, kind, ok in files(img):
        print('%-12s unit %3d x%-2d len $%06x  %-6s -> %6d bytes%s  checksums %s%s' % (
            name, unit, count, length, kind, len(body),
            '' if len(body) == length else ' (LENGTH MISMATCH)', 'ok' if ok else 'BAD',
            '  amiga hunk' if body[:4] == b'\0\0\x03\xf3' else ''))
        if outdir:
            open(os.path.join(outdir, name), 'wb').write(body)


if __name__ == '__main__':
    main()
