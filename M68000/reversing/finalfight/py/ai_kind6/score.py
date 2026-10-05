#!/usr/bin/env python3
"""score.py <frames.bin>: Cody's score long (+132, BCD) changes versus the kind-6 death sequence (2: 2->4 .. record freed)"""
import sys
FS = 13*192 + 2*192 + 0x200
d = open(sys.argv[1], 'rb').read(); n = len(d)//FS
def cody(fr): return d[fr*FS + 13*192: fr*FS + 14*192]
def kr(fr):
    for i in range(13):
        r = d[fr*FS + i*192: fr*FS + (i+1)*192]
        if r[0] and r[19] == 6: return r
sc = lambda fr: cody(fr)[132:136].hex()
prev = None; pk = None
for fr in range(n):
    s = sc(fr)
    r = kr(fr)
    st = (r[2], r[20]) if r else None
    if pk is not None and st != pk and st and st[0] in (4, 6): print('f%d kind-6 state %s char %d (killer kind 105=%d 162=%d)' % (fr, st[0], r[20], r[105], r[162]))
    pk = st
    if prev is not None and s != prev: print('f%d score %s -> %s' % (fr, prev, s))
    prev = s
