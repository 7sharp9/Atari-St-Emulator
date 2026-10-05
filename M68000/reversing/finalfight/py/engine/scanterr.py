#!/usr/bin/env python3
"""scanterr.py <gfx.bin> : histogram of the terrain code (attribute word bits 15..10) over the scroll-2 map $90c000..$90ffff (16 KB, 4 bytes per tile: code, attr)
and, for codes 3 and 5, the runs of consecutive entries (the 80-entry marker blocks)."""
import sys
d = open(sys.argv[1], 'rb').read()
base = 0xc000   # $90c000 - $900000
w = lambda a: int.from_bytes(d[a:a+2], 'big')
hist = {}
cols = {}
for k in range(0, 0x4000, 4):
    attr = w(base + k + 2)
    t = attr >> 10
    hist[t] = hist.get(t, 0) + 1
print('terrain code histogram:', dict(sorted(hist.items())))
for code in (3, 5):
    ents = [k for k in range(0, 0x4000, 4) if (w(base + k + 2) >> 10) == code]
    runs = []
    for k in ents:
        if runs and k - runs[-1][1] == 4: runs[-1][1] = k
        else: runs.append([k, k])
    print('code', code, 'entries', len(ents), 'runs (byte offset from $90c000, entries):', [(hex(a), (b - a) // 4 + 1) for a, b in runs][:20])
