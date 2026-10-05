#!/usr/bin/env python3
"""hitlog.py dodge|mask <hits file written by k6hit.lua>
 dodge: lines from K6_BP="3a454|E d=%x st=%x|b@(a3+0x60),b@(a3+2);3a48a|N d=%x rnd=%x mask=%x|b@(a3+0x60),d0,d1;3a492|Y d=%x|b@(a3+0x60)"
        counts evaluations (N), dodges (Y) and the dodges predicted by (mask >> (rnd & 31)) & 1.
 mask:  lines from K6_BP="3a53a|M ch=%x d96=%x mask=%x rnd=%x|b@(a6+0x14),b@(a6+0x60),d1,d0"
        compares the attack-start mask with word[$3a53e+2d] (the code's real table) and the character's own table ($3a542/$3a582)."""
import re, sys, os
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../../..'))
rom = open(os.path.join(ROOT, 'scratchpad/finalfight/ff_main.bin'), 'rb').read()
w = lambda a: int.from_bytes(rom[a:a+2], 'big')
mode, path = sys.argv[1], sys.argv[2]
L = open(path).read().split('\n')
if mode == 'dodge':
    N = [l for l in L if l.startswith('H N')]; Y = [l for l in L if l.startswith('H Y')]; E = [l for l in L if l.startswith('H E')]
    pred = 0; agree = 0
    for l in N:
        m = re.match(r'H N d=\w+ rnd=(\w+) mask=(\w+)', l); rnd = int(m.group(1), 16); mask = int(m.group(2), 16)
        pred += (mask >> (rnd & 31)) & 1
    print('entries %d, evaluations past the preconditions %d, dodges %d, dodges predicted by (mask>>rnd)&1: %d' % (len(E), len(N), len(Y), pred))
else:
    tot = main = own = poi = poi_own = 0
    for l in L:
        m = re.match(r'H M ch=(\w+) d96=(\w+) mask=(\w+) rnd=(\w+)', l)
        if not m: continue
        ch, d, mask, rnd = [int(x, 16) for x in m.groups()]
        tot += 1; main += mask == w(0x3a53e + 2*d)
        if ch == 1: poi += 1; poi_own += mask == w(0x3a582 + 2*d)
        else: own += mask == w(0x3a542 + 2*d)
    print('evaluations %d (Poison %d); mask == word[$3a53e+2d]: %d; Roxy mask == its own table $3a542+2d: %d of %d; Poison mask == its own table $3a582+2d: %d of %d' % (tot, poi, main, own, tot - poi, poi_own, poi))
