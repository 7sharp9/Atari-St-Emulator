"""Probe: the enemy-hit shield cost at $ccb0..$ccc4 reads $159aa[level] as a pointer. Set the level word 662(A6)
(and 725 to the current $c099 so no level-up fires), run to the load at $ccc0, report the pointer, the index
(type x 2), the cost word there and the shield 608(A6) before and after the subtract. Control: the same run at level 3.

    cd M68000 && python3 reversing/starglider/py/curios/shield_level.py
"""
import os, sys
here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(here, '..', 'flight'))
from flightlib import *
OUTDIR = sg.work('curios'); os.makedirs(OUTDIR, exist_ok=True)
dr = sd.Drive(ROOT, journal=os.path.join(OUTDIR, 'j_shield.jsonl'), period=POLL)
dr.load(sg.SNAP_GAME1, sg.DISK)
start = dr.fork()
for level in [int(x) for x in sys.argv[1:]] or (3, 16, 20, 31):
    dr.restore(start)
    dr.poke(G + 662, 2, level)
    dr.poke(G + 725, 1, dr.u8(0xc099))
    hits = 0
    for _ in range(3):
        r = dr.run(40_000_000, until_pc=0xccc0)
        if r['reason'] != 'until':
            print(f'level {level}: stopped {r["reason"]} after {r["steps"]} steps'); break
        g = dr.rpc('regs'); g = g[0] if isinstance(g, list) else g
        a0 = int(str(g['a0']).lstrip('$'), 16); d0 = int(str(g['d0']).lstrip('$'), 16) & 0xffff
        cost = dr.u16((a0 + d0) & 0xffffff)
        sh = dr.u16(G + 608)
        dr.step(2)
        print(f'level {dr.s16(G+662)}: ptr {a0:#08x} idx {d0:#x} cost word {cost:#06x} ({cost}) shield {sh}->{dr.u16(G+608)}')
        hits += 1
dr.close()
