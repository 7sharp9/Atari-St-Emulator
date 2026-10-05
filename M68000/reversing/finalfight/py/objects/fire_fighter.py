#!/usr/bin/env python3
"""fire_fighter.py <log>... : for logs from fire_run.sh with a fighter, list the frames where the fire's attack box overlaps the fighter's hurt box ($7932 replay),
the value of the frame counter 167(A5) there, and the frame the fighter's hp fell by 40. The fire hits fighters only from $639e, which the fire handler calls when
((167(A5) >> 1) + D7) & 3 == 0 (D7 = 0 for pool a record 15, where the fire sits)."""
import os, sys
here = os.path.dirname(os.path.abspath(__file__))
root = os.environ.get('M68000_ROOT') or os.path.abspath(os.path.join(here, '../../../..'))
rom = open(os.path.join(root, 'scratchpad/finalfight/ff_main.bin'), 'rb').read()
def rw(a): return int.from_bytes(rom[a:a+2], 'big')
def w(h, o): return int(h[2*o:2*o+4], 16)
def l(h, o): return int(h[2*o:2*o+8], 16)
for log in sys.argv[1:]:
    rel = None; c = None; fire = None; bred = None; first = None; lasthp = None
    over = []; hit = None
    frames = []
    for line in open(log):
        p = line.split()
        if line.startswith('F '):
            if fire is not None and bred is not None: frames.append((rel, c, fire, bred))
            fire = None; bred = None
            rel = int(p[2].split('=')[1]); c = int([x for x in p if x.startswith('c167=')][0].split('=')[1], 16)
        elif line.startswith('R '):
            h = p[3]
            if p[1] == 'a' and int(h[38:40], 16) == 0x10: fire = h
            if p[1] == '2' and int(h[38:40], 16) == 0 and int(h[40:42], 16) == 0 and w(h, 6) in (0x1c0 + 0, 0x1c0 + 28, 0x1c0 + 40, 0x1c0 - 41, 0x1c0 + 80, 0x1c0 - 65, 0x1c0 + 64): bred = h
    for rel, c, fire, bred in frames:
        if first is None: first = rel
        pa, ph = l(fire, 112) & 0xffffff, l(bred, 120) & 0xffffff
        hp = w(bred, 24)
        if lasthp is not None and hit is None and hp != lasthp and hp >= 0xff00 and lasthp < 0x80: hit = (rel - first, c)
        lasthp = hp
        if pa and ph:
            ax, ay, hx, hy = w(fire, 116), w(fire, 118), w(bred, 124), w(bred, 126)
            s = rw(pa + 4) + rw(ph + 4); s2 = rw(pa + 6) + rw(ph + 6)
            if ((hx - ax + s) & 0xffff) <= 2 * s and ((hy - ay + s2) & 0xffff) <= 2 * s2: over.append((rel - first, c, (c >> 1) & 3))
    print(log, 'overlap frames (fire+n, c167, (c167>>1)&3):', over[:14], '... total', len(over), ' fighter hit (fire+n, c167):', hit)
