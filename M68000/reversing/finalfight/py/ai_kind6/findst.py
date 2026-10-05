#!/usr/bin/env python3
"""findst.py <frames.bin> <sub-state value 3(A6)> : frames where the kind-6 record enters that sub-state (main state 2)"""
import sys
FS = 13*192 + 2*192 + 0x200
d = open(sys.argv[1], 'rb').read(); n = len(d)//FS
v = int(sys.argv[2]); prev = {}
out = []
for fr in range(n):
    for i in range(13):
        r = d[fr*FS + i*192: fr*FS + (i+1)*192]
        if r[0] and r[19] == 6 and r[2] == 2:
            if prev.get(i) is not None and prev[i] != r[3] and r[3] == v: out.append((fr, prev[i]))
            prev[i] = r[3]
        else: prev.pop(i, None)
print(out)
