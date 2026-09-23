#!/usr/bin/env python3
r"""Make a headless-bootable copy of the Populous [cr Replicants] disk.

The crack boots to the GEM desktop and expects LOADER.TOS to be double-clicked. This copy
moves LOADER.TOS into \AUTO\LOADER.PRG so TOS runs it at boot. The disk is full, so the
LOADER.TOS and DESKTOP.INF entries are freed first (3 clusters: AUTO dir + 2 for the loader).
Nothing else on the disk changes.

    python reversing/populous/make_disk.py "Populous (1989)(Bullfrog)[cr Replicants].st" pop_auto.st
"""
import os
import struct
import subprocess
import sys
import tempfile

src, dst = sys.argv[1], sys.argv[2]
d = bytearray(open(src, 'rb').read())
bps = struct.unpack_from('<H', d, 11)[0]
res = struct.unpack_from('<H', d, 14)[0]
nfat, spf = d[16], struct.unpack_from('<H', d, 22)[0]
nroot = struct.unpack_from('<H', d, 17)[0]
root = (res + nfat * spf) * bps
data0 = root + nroot * 32
spc = d[13]


def fat_set(c, v):
    for f in range(nfat):
        o = res * bps + f * spf * bps + c * 3 // 2
        if c & 1:
            d[o] = (d[o] & 0x0f) | ((v & 0xf) << 4); d[o + 1] = v >> 4
        else:
            d[o] = v & 0xff; d[o + 1] = (d[o + 1] & 0xf0) | (v >> 8)


def fat_get(c):
    o = res * bps + c * 3 // 2
    v = d[o] | d[o + 1] << 8
    return v >> 4 if c & 1 else v & 0xfff


loader = None
for i in range(nroot):
    e = root + i * 32
    name = bytes(d[e:e + 11])
    if name in (b'LOADER  TOS', b'DESKTOP INF'):
        c = struct.unpack_from('<H', d, e + 26)[0]
        n = struct.unpack_from('<I', d, e + 28)[0]
        body = b''
        while c < 0xff0:
            body += d[data0 + (c - 2) * spc * bps:data0 + (c - 1) * spc * bps]
            nxt = fat_get(c); fat_set(c, 0); c = nxt
        if name == b'LOADER  TOS':
            loader = body[:n]
        d[e] = 0xe5
if loader is None:
    sys.exit("LOADER.TOS not found - wrong disk?")
with tempfile.TemporaryDirectory() as t:
    trimmed, prg = os.path.join(t, 'trim.st'), os.path.join(t, 'LOADER.PRG')
    open(trimmed, 'wb').write(d)
    open(prg, 'wb').write(loader)
    tool = os.path.join(os.path.dirname(__file__), '..', '..', 'tools', 'add_file_to_disk.py')
    subprocess.run([sys.executable, tool, trimmed, prg, '--auto', '--out', dst], check=True)
