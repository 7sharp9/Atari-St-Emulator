"""The attract loop ($13816 main) calls the drone-demo race $caa8(track) and then advances the track with the -8526(A4)
permutation table; record which track each successive attract demo plays (argument at 4(A7) on entry to $caa8)."""
import sys; sys.path.insert(0,'.')
from tkcommon import *
r = Repl2(sscfg.SNAP_ATTRACT)
seq = []
for k in range(9):
    o, reg = r.cmd2('bpc caa8 1 25000000')
    if reg['PC'] != 0xcaa8: print('no further $caa8 entry within budget at hit', k); break
    trk = int.from_bytes(r.mem(reg['A7'] + 4, 2), 'big'); seq.append(trk)
    r.cmd('s 2000')                                    # get past the entry so the next bpc finds the next call
print('attract demo tracks (0-based) in successive attract cycles:', seq)
print('-8526(A4) permutation:', [int.from_bytes(r.mem(A4 - 8526 + 2*i, 2), 'big') for i in range(8)])
r.close()
