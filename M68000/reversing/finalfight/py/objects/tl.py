#!/usr/bin/env python3
"""tl.py <log> [pools] [fields]: compact timeline of an sp.lua log. Prints, per live record of the selected pools (default 8,a,6,4), one line per change of the chosen fields:
frame(rel) pool addr  +18/+19/+20/+21, state bytes +2 +3 +4 +5, x y, +24 hp, +45 atk idx, +44 hurt, +63, +60, +22.  Usage: tl.py log.txt 6,a  (pool names as in the log)."""
import sys
log = sys.argv[1]
pools = set((sys.argv[2] if len(sys.argv) > 2 else '8,a,6,4').split(','))
rel = None; prev = {}
def b(h, o): return int(h[2*o:2*o+2], 16)
def w(h, o): return int(h[2*o:2*o+4], 16)
for l in open(log):
    p = l.split()
    if l.startswith('F '):
        rel = int(p[2].split('=')[1]); cam = p[3]; pl = p[5]
    elif l.startswith('SPAWN'):
        print(l.rstrip())
    elif l.startswith('R ') and p[1] in pools:
        h = p[3]
        key = (b(h,2), b(h,3), b(h,4), b(h,5), b(h,19), b(h,20), b(h,45), b(h,44), w(h,24), b(h,63), b(h,0), b(h,1), b(h,99))
        if prev.get(p[2]) != key:
            prev[p[2]] = key
            print('%5d %-3s %s k=%02x/%02x/%02x st=%02x.%02x.%02x.%02x x=%04x y=%04x g=%04x hp=%04x atk=%02x hurt=%02x r63=%02x +60=%04x +22=%02x b0=%02x b1=%02x 99=%02x 74=%02x 64=%02x 66=%02x 30=%02x' % (
                rel, p[1], p[2], b(h,18), b(h,19), b(h,20), b(h,2), b(h,3), b(h,4), b(h,5), w(h,6), w(h,10), w(h,14), w(h,24), b(h,45), b(h,44), b(h,63), w(h,60), b(h,22), b(h,0), b(h,1), b(h,99), b(h,74), b(h,64), b(h,66), b(h,30)))
    elif l.startswith('X ') and p[1] in pools:
        print('%5d %-3s %s FREED' % (rel, p[1], p[2])); prev.pop(p[2], None)
