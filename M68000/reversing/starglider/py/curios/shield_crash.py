"""Probe: at levels 32 and 34 the collision-cost pointer $159aa[level] is $500050 / $500500 (unmapped on an ST).
Run to the load at $ccc0, then single-step it and report PC, SR and the stop reason; render the screen after 2M steps.
Control: level 3. Same snapshot (g_game1), same budget.

    cd M68000 && python3 reversing/starglider/py/curios/shield_crash.py
"""
import os, sys
here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(here, '..', 'flight'))
from flightlib import *
OUTDIR = sg.work('curios'); os.makedirs(OUTDIR, exist_ok=True)
dr = sd.Drive(ROOT, journal=os.path.join(OUTDIR, 'j_crash.jsonl'), period=POLL)
dr.load(sg.SNAP_GAME1, sg.DISK)
start = dr.fork()
def regs():
    g = dr.rpc('regs'); return g[0] if isinstance(g, list) else g
for level in (3, 32, 34):
    dr.restore(start)
    dr.poke(G + 662, 2, level); dr.poke(G + 725, 1, dr.u8(0xc099))
    r = dr.run(40_000_000, until_pc=0xccc0)
    g = regs()
    print(f'level {level}: run -> {r["reason"]} after {r["steps"]} steps, PC {g["pc"]} A0 {g.get("a0")} D0 {g.get("d0")}')
    for i in range(4):
        dr.step(1); g = regs()
        print(f'   step {i+1}: PC {g["pc"]} SR {g.get("sr")} D0 {g.get("d0")}')
    dr.step(2_000_000); g = regs()
    print(f'   +2M: PC {g["pc"]} 300={dr.u16(G+300)} shield={dr.u16(G+608)}')
    dr.rpc('render', path=os.path.join(OUTDIR, f'crash_L{level}.png'))
dr.close()
