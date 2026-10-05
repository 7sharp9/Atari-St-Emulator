#!/usr/bin/env python3
"""gate_score.py <frames.bin>...: at the frame a kind-6 record enters state 6 (despawn) Cody's score long (+132, BCD) rises by
$00002000 (Roxy) or $00003000 (Poison) (rows $17, $06 of the table at $1b26 awarded through $288c/$1a22)."""
import sys
FS = 13*192 + 2*192 + 0x200
ok = bad = 0; rows = []
for path in sys.argv[1:]:
    d = open(path, 'rb').read(); n = len(d)//FS
    prev = {}
    for fr in range(1, n):
        for i in range(13):
            r = d[fr*FS + i*192: fr*FS + (i+1)*192]
            if r[0] and r[19] == 6:
                p = prev.get(i)
                if p is not None and p != 6 and r[2] == 6:
                    s0 = int(d[(fr-1)*FS + 13*192 + 132: (fr-1)*FS + 13*192 + 136].hex()); s1 = int(d[fr*FS + 13*192 + 132: fr*FS + 13*192 + 136].hex())
                    exp = 2000 if r[20] == 0 else 3000
                    if s1 - s0 == exp: ok += 1
                    else: bad += 1; rows.append((path, fr, r[20], s1 - s0))
                prev[i] = r[2]
            else: prev.pop(i, None)
print('state 6 entries with the expected score award: %d of %d' % (ok, ok + bad)); print(rows[:6])
