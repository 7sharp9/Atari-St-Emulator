#!/usr/bin/env python3
"""Generator-side checks for the final base (D0 = 10, D2 = 1) from the mission-1 stage dumps (`py/mapgen/full/`,
`common.load`): (1) the first stage whose dump holds a group record at $1d33a, and that record (compare with the
in-play record from guard.py); (2) the module's 13270 (the generator's own A6 block, as `full/stagestats.py` reads it; not federation's
13270(A6)) against the number of lock records (byte 9 = $20) at every stage.
  uv run python -I reversing/captive/py/world/station/gencheck.py"""
import os, sys
d = os.path.dirname(os.path.abspath(__file__))
while not os.path.exists(os.path.join(d, 'tools', 'rdis.py')):
    nd = os.path.dirname(d)
    if nd == d: sys.exit('repo root not found')
    d = nd
sys.path.insert(0, os.path.join(d, 'reversing', 'captive', 'py', 'mapgen', 'full'))
import groups as G, common  # noqa: E402
A6 = 0x1b5ce; FED = common.FED
recs = common.load(1, 10)
first = None
for (stop, callee), (_, m, f) in zip(common.STAGES, recs):
    w = lambda o: (m[o] << 8) | m[o + 1]
    nlocks = sum(1 for i in range(32) if f[0x1d782 - FED + 10 * i + 9] == 0x20)
    rec = None; p = 0x1c782
    for g in G.groups(f):
        if p == 0x1d33a: rec = g; break
        p += len(g)
    if rec is not None and first is None:
        first = stop; print(f'record at $1d33a first in stage {stop:#x} (callee {callee:#x}): ({rec[0]},{rec[1]}) {rec.hex()}')
    print(f'stage {stop:#x}: module 13270 = {w(13270)}, lock records {nlocks}')
