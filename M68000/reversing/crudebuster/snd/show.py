#!/usr/bin/env python3
"""show.py <lo-hex> <hi-hex> : print rd.txt lines for physical addresses [lo,hi)"""
import sys, re
lo, hi = int(sys.argv[1], 16), int(sys.argv[2], 16)
for l in open(__file__.rsplit('/', 1)[0] + '/rd.txt'):
    m = re.match(r'([0-9a-f]{5}) ', l)
    if m and lo <= int(m.group(1), 16) < hi: print(l.rstrip()[:78])
    elif l.startswith('  ;') and False: print(l.rstrip())
