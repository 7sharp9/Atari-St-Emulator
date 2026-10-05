#!/usr/bin/env python3
"""idmap.py : classify every sound command byte $00..$ff by the sound CPU response measured in the z80sweep runs (out/z80sweep_{full,A,B,C}.txt):
 oki phrase (started phrase number), ym music (YM2151 key-ons), or silent. Prints ranges."""
import re, os, sys, collections
here = os.path.dirname(os.path.abspath(__file__)); root = os.environ.get('M68000_ROOT') or os.path.abspath(os.path.join(here, '..', '..', '..', '..')); base = os.environ.get('FFB_BASE') or os.path.join(root, 'scratchpad', 'finalfight', 'engine')
res = {}
for n in ('full', 'A', 'B', 'C'):
    p = os.path.join(base, 'out', 'z80sweep_%s.txt' % n)
    if not os.path.exists(p): continue
    marks = []; evs = []; ym = []
    reg = None
    for l in open(p):
        m = re.match(r'f=(\d+) S id=([0-9a-f]+)', l)
        if m: marks.append((int(m.group(1)), int(m.group(2), 16))); continue
        m = re.match(r'f=(\d+) Z w a=f002 d=([0-9a-f]+)', l)
        if m: evs.append((int(m.group(1)), int(m.group(2), 16))); continue
        m = re.match(r'f=(\d+) Z ym a=([0-9a-f]+) d=([0-9a-f]+)', l)
        if m:
            a = int(m.group(2), 16); d = int(m.group(3), 16)
            if a == 0xf000: reg = d
            elif reg == 0x08 and (d >> 3) & 15: ym.append(int(m.group(1)))
    for i, (f, d) in enumerate(marks):
        end = min(f + 150, marks[i + 1][0] - 41) if i + 1 < len(marks) else f + 150
        b = [x for (ff, x) in evs if f <= ff < end]
        phr = []; pend = None
        for x in b:
            if pend is not None: phr.append((pend, x >> 4)); pend = None
            elif x & 0x80: pend = x & 0x7f
        keyons = sum(1 for ff in ym if f <= ff < end)
        res[d] = (phr, keyons)
def cls(d):
    phr, k = res.get(d, ([], None))
    if k is None: return 'not swept'
    if phr and phr[0][0] != 0 and k <= 1: return 'oki %02x' % phr[0][0]
    if k > 1: return 'music (ym key-ons %d)%s' % (k, (' + oki %02x' % phr[0][0]) if phr else '')
    return 'silent'
runs = []
for d in range(256):
    c = cls(d)
    if runs and runs[-1][2] == c and (c.startswith('silent') or c.startswith('not')): runs[-1][1] = d
    else: runs.append([d, d, c])
for a, b, c in runs: print('%02x-%02x  %s' % (a, b, c) if a != b else '%02x     %s' % (a, c))
oki = [(d, res[d][0][0][0]) for d in range(256) if d in res and res[d][1] <= 1 and res[d][0] and res[d][0][0][0]]
print('oki ids:', len(oki), 'of which phrase == (id & 0x3f) + 1:', sum(1 for d, p in oki if p == (d & 0x3f) + 1))
