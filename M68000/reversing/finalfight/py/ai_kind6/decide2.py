#!/usr/bin/env python3
"""decide2.py <frames.bin>: classify each attack start (3: 2->4) by the trigger path of $3a4a4:
 A: player within |dx|<=$40,|dy|<=9 (161=1)  B: within |dx|<$50,|dy|<=9 (no 161)  C: lane timer (148(A6) 30-frame countdown + random mask)
 and check the id against the $3abee row (window of 1..8 frames after the transition)."""
import sys, collections, os
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..'))
rom = open(os.path.join(ROOT, 'scratchpad/finalfight/ff_main.bin'), 'rb').read()
FS = 13*192 + 2*192 + 0x200
d = open(sys.argv[1], 'rb').read(); n = len(d)//FS
w = lambda r, o: int.from_bytes(r[o:o+2], 'big')
sw = lambda r, o: w(r, o) - 65536 if w(r, o) & 0x8000 else w(r, o)
def rec(fr, i): return d[fr*FS + i*192: fr*FS + (i+1)*192]
def cody(fr): return d[fr*FS + 13*192: fr*FS + 14*192]
prev = {}; ev = []
for fr in range(n):
    for i in range(13):
        r = rec(fr, i)
        if r[0] and r[19] == 6:
            p = prev.get(i)
            if p and p[0] == 2 and p[1] == 2 and r[2] == 2 and r[3] == 4 and r[4] == 0: ev.append((fr, i))
            prev[i] = (r[2], r[3])
        else: prev.pop(i, None)
paths = collections.Counter(); idok = collections.Counter(); dwell = []
for fr, i in ev:
    r0 = rec(fr - 1, i); c0 = cody(fr - 1)
    ch = r0[20]
    dx = abs(w(c0, 6) - w(r0, 6)); dy = sw(c0, 14) - sw(r0, 14)   # 3a65c uses 10(A0) (y) not 14 ; use y
    dyy = sw(c0, 10) - sw(r0, 10)
    air = w(c0, 90)
    if dx <= 0x40 and abs(dyy) <= 9 and air == 0: path = 'A'
    elif dx < 0x50 and abs(dyy) <= 9 and air == 0: path = 'B'
    else: path = 'C'
    paths[(ch, path)] += 1
    # dwell: frames since 148(A6) became nonzero
    k = fr - 1; 
    while k > 0 and rec(k, i)[148] != 0 and rec(k, i)[3] == 2: k -= 1
    if path == 'C': dwell.append(fr - 1 - k)
    # id check
    dd = abs(w(cody(fr + 1), 6) - w(rec(fr + 1, i), 6))
    band = 7 if dd >= 0x100 else (0 if dd < 0x40 else 1 + (dd - 0x40)//0x20)
    row = rom[0x3abee + 0x100*ch + 32*band: 0x3abee + 0x100*ch + 32*band + 32]
    got = None
    for k2 in range(1, 9):
        rk = rec(fr + k2, i)
        if rk[3] == 4 and rk[147] == 1 and rk[2] == 2: got = rk[149]; break
    idok[(got in row) if got is not None else 'none'] += 1
print('trigger paths (char,path):', sorted(paths.items()))
print('lane-timer dwell frames (C):', sorted(dwell))
print('id in the $3abee row of the dx band (1..8 frame window):', dict(idok))
