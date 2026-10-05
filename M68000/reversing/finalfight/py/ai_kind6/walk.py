#!/usr/bin/env python3
"""walk.py <frames.bin>...: walking facts: speed per frame, pause counter 143 values, slot target offsets 138/132 relative to the player"""
import sys, collections
FS = 13*192 + 2*192 + 0x200
w = lambda r, o: int.from_bytes(r[o:o+2], 'big')
sw = lambda r, o: w(r, o) - 65536 if w(r, o) & 0x8000 else w(r, o)
pauses = collections.Counter(); stepx = collections.Counter(); stepy = collections.Counter(); off = collections.Counter(); heads = collections.Counter()
n143 = 0
for path in sys.argv[1:]:
    d = open(path, 'rb').read(); n = len(d)//FS
    prev = {}
    for fr in range(n):
        c = d[fr*FS + 13*192: fr*FS + 14*192]
        for i in range(13):
            r = d[fr*FS + i*192: fr*FS + (i+1)*192]
            if r[0] and r[19] == 6 and r[2] == 2 and r[3] == 2:
                p = prev.get(i)
                if p:
                    if p[0] == 0 and r[143] > 0: pauses[r[143]] += 1
                    if r[4] == 2 and r[143] == 0 and p[0] == 0:
                        # heading 8 or 24: pure horizontal
                        if r[54] in (8, 24): stepx[abs(w(r, 6) - p[1])] += 1
                        if r[54] in (0, 16): stepy[abs(sw(r, 10) - p[2])] += 1
                if r[4] == 2 and r[142] == 1 or True: pass
                prev[i] = (r[143], w(r, 6), sw(r, 10))
            else: prev.pop(i, None)
            # slot offsets: when 138 set during approach (3=4,4=2,5=2)
            if r[0] and r[19] == 6 and r[2] == 2 and r[3] == 4 and r[4] == 2 and r[5] == 2:
                off[(r[149] < 6, abs(sw(r, 138)))] += 1
print('pause 143 initial values (frames):', sorted(pauses.items()))
print('|dx| per frame at headings 8/24 (steady walking):', sorted(stepx.items()))
print('|dy| per frame at headings 0/16:', sorted(stepy.items()))
print('approach stand-off |138| by (id<6):frames', sorted(off.items()))
