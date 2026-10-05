#!/usr/bin/env python3
"""fire_phase.py <log>... : fire against a fighter at different start phases (fire_run.sh ... <at>). For each log: the predicted hit (an overlap in a frame's dump followed by a frame whose
c167 satisfies ((c167>>1)&3)==0, the $639e gate with D7=0) against the observed hp fall of the fighter."""
import os, sys, re
here = os.path.dirname(os.path.abspath(__file__))
root = os.environ.get('M68000_ROOT') or os.path.abspath(os.path.join(here, '../../../..'))
rom = open(os.path.join(root, 'scratchpad/finalfight/ff_main.bin'), 'rb').read()
def rw(a): return int.from_bytes(rom[a:a+2], 'big')
def w(h, o): return int(h[2*o:2*o+4], 16)
def l(h, o): return int(h[2*o:2*o+8], 16)
tot = ok = 0
for log in sys.argv[1:]:
    frames = []; rel = None; c = None; fire = None; bred = None
    fx = int(re.search(r'fx=(\w+)', open(log).readline() or '').group(1), 16) if False else None
    for line in open(log):
        p = line.split()
        if line.startswith('F '):
            if fire is not None and bred is not None: frames.append((rel, c, fire, bred))
            fire = None; bred = None
            rel = int(p[2].split('=')[1]); c = int([x for x in p if x.startswith('c167=')][0].split('=')[1], 16)
        elif line.startswith('R '):
            h = p[3]
            if p[1] == 'a' and int(h[38:40], 16) == 0x10: fire = h
            if p[1] == '2' and int(h[38:40], 16) == 0 and int(h[40:42], 16) == 0 and 0x1c0 - 100 < w(h, 6) < 0x1c0 + 100 and w(h, 10) == 0x36: bred = h
    first = frames[0][0]; pred = None; obs = None; lasthp = None
    for i, (rel, c, fire, bred) in enumerate(frames):
        hp = w(bred, 24)
        if lasthp is not None and obs is None and hp >= 0xff00 and lasthp < 0x80: obs = rel - first
        lasthp = hp
        if i + 1 < len(frames) and pred is None:
            pa, ph = l(fire, 112) & 0xffffff, l(bred, 120) & 0xffffff
            if pa and ph:
                ax, ay, hx, hy = w(fire, 116), w(fire, 118), w(bred, 124), w(bred, 126)
                s = rw(pa + 4) + rw(ph + 4); s2 = rw(pa + 6) + rw(ph + 6)
                if ((hx - ax + s) & 0xffff) <= 2 * s and ((hy - ay + s2) & 0xffff) <= 2 * s2 and ((frames[i+1][1] >> 1) & 3) == 0:
                    pred = frames[i+1][0] - first
    tot += 1; ok += (pred == obs)
    print(log, 'first frame c167=%d' % frames[0][1], 'predicted hit fire+%s' % pred, 'observed fire+%s' % obs, 'MATCH' if pred == obs else 'DIFF')
print('match %d of %d' % (ok, tot))
