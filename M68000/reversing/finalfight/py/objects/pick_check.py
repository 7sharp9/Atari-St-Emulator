#!/usr/bin/env python3
"""pick_check.py <log>... : pickup test of a hand-placed pool 6 weapon at the player's feet. Prints the weapon's state/mode and +64/+74/+66 before the press (rel 229), after it (rel 260),
the player's +90 (held weapon pointer), +2/+3/+4 state bytes around the press, and whether +90 became non-zero."""
import sys
def b(h, o): return int(h[2*o:2*o+2], 16)
def w(h, o): return int(h[2*o:2*o+4], 16)
for log in sys.argv[1:]:
    rel = None; P = {}; W = {}
    for line in open(log):
        p = line.split()
        if line.startswith('F '): rel = int(p[2].split('=')[1])
        elif line.startswith('R '):
            if p[1] == 'P': P[rel] = p[3]
            if p[1] == '6' and b(p[3], 18) == 6: W[rel] = p[3]
    def at(d, r):
        ks = [k for k in sorted(d) if k <= r]
        return d[ks[-1]] if ks else None
    print(log)
    for r in (229, 232, 236, 245, 260, 299):
        P1, W1 = at(P, r), at(W, r)
        print('  rel %d player st=%02x.%02x.%02x +90=%04x | weapon k=%02x st=%02x.%02x.%02x 64=%02x 66=%02x 74=%02x x=%04x y=%04x' % ((r, b(P1, 2), b(P1, 3), b(P1, 4), w(P1, 90)) + ((b(W1, 19), b(W1, 2), b(W1, 3), b(W1, 4), b(W1, 64), b(W1, 66), b(W1, 74), w(W1, 6), w(W1, 10)) if W1 else (0,) * 9)))
