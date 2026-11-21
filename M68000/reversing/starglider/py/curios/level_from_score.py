"""Probe: the level word 662(A6) follows the score's ten-thousands byte $c099 ($fbb8: any change of $c099 -> level+1,
capped at 34). Practice flag 717 poked on, then N tapped repeatedly (N = pending score $5000 in practice mode, $d4d8);
print score and level after each tap. Control: the same taps with 717 = 0 (N does nothing).

    cd M68000 && python3 reversing/starglider/py/curios/level_from_score.py [taps]
"""
import os, sys
here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(here, '..', 'flight'))
from flightlib import *
OUTDIR = sg.work('curios'); os.makedirs(OUTDIR, exist_ok=True)
taps = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 8
dr = sd.Drive(ROOT, journal=os.path.join(OUTDIR, 'j_level.jsonl'), period=POLL)
dr.load(sg.SNAP_GAME1, sg.DISK)
start = dr.fork()
for flag in (0xff, 0):
    dr.restore(start); dr.poke(G + 717, 1, flag)
    seen = []
    for i in range(taps):
        dr.hold(sd.Key(0x31), steps=60000); dr.step(4 * POLL)
        seen.append((dr.read(0xc098, 4).hex(), dr.s16(G + 662)))
    print(f'717={flag:#x}:', ' '.join(f'{s}/L{l}' for s, l in seen))
dr.close()

# with --crash: after the taps (practice on), run to the collision-cost load $ccc0, step past it, report and render
if '--crash' in sys.argv:
    dr = sd.Drive(ROOT, journal=os.path.join(OUTDIR, 'j_level_crash.jsonl'), period=POLL)
    dr.load(sg.SNAP_GAME1, sg.DISK); dr.poke(G + 717, 1, 0xff)
    while dr.s16(G + 662) < 32:
        dr.hold(sd.Key(0x31), steps=100000); dr.step(4 * POLL)
    print('score', dr.read(0xc098, 4).hex(), 'level', dr.s16(G + 662), 'step', dr.step_count)
    r = dr.run(60_000_000, until_pc=0xccc0)
    g = dr.rpc('regs'); g = g[0] if isinstance(g, list) else g
    print('run ->', r['reason'], r['steps'], 'PC', g['pc'], 'A0', g['a0'], 'level', dr.s16(G + 662))
    dr.step(1); g = dr.rpc('regs'); g = g[0] if isinstance(g, list) else g
    print('after the load: PC', g['pc'])
    dr.step(3_000_000)
    dr.rpc('render', path=os.path.join(OUTDIR, 'natural_L32.png'))
    dr.close()
