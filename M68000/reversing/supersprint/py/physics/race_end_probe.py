"""race_end_probe.py - what happens at the frame where test_trajectory (seed 2) starts to diverge? Replays the same natural drive and prints lap counters and
the end-of-race latch around the first diverging frame (1181), and whether the per-car control routines still run (hits of $eaea/$d4fa per frame)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from difflib_ss import *
h = Harness(sscfg.SNAP_RACE)
drv = Driver(h, 2)
for i in range(1190):
    drv.poke_input()
    if h.run_to(0xdf18, 1) is None:
        print('bpc lost at', i); break
    if i >= 1170 and i % 2 == 0:
        m = P.Mem(h.snap_ram().b)
        print(i, 'LAPS', [m.a(P.LAPS, c) for c in range(4)], '-4822', [m.a(-4822, c) for c in range(4)], '-1802', m.g(-1802), 'SPD', [m.a(P.SPD, c) for c in range(4)])
out, _ = h.cmd('hits 100000 d4fa eaea df18')
print('\n'.join(l for l in out if 'first' in l))
h.close()
