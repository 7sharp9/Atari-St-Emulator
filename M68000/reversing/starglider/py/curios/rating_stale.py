"""Probe: the pilot rating ($13596) is grade[min(level * 670 / 100, 11)] with 670 = hits*100/shots (byte), and with
0 shots it skips the 670 update, so the grade uses 670 as left by an earlier game (670's only writer is $135fc; raw
scan). Legs from g_game1, energy poked to 1 to end the game, shots = hits = 0, level 10:
  670 = 100 (a stale 100% accuracy)  -> expect CHEAT!?!   (index 10)
  670 = 0                            -> expect ROOKIE     (control)
Stops at $13646 (rating page drawn, before the key wait) and renders it.

    cd M68000 && python3 reversing/starglider/py/curios/rating_stale.py
"""
import os, sys
here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(here, '..', 'flight'))
from flightlib import *
OUTDIR = sg.work('curios'); os.makedirs(OUTDIR, exist_ok=True)
dr = sd.Drive(ROOT, journal=os.path.join(OUTDIR, 'j_rating.jsonl'), period=POLL)
dr.load(sg.SNAP_GAME1, sg.DISK)
start = dr.fork()
for acc in (100, 0):
    dr.restore(start)
    dr.poke(G + 176, 4, 0); dr.poke(G + 184, 4, 0); dr.poke(G + 670, 2, acc)
    dr.poke(G + 662, 2, 10); dr.poke(G + 725, 1, dr.u8(0xc099)); dr.poke(G + 606, 2, 1)
    r = dr.run(30_000_000, until_pc=0x13646)
    print(f'670={acc}: {r["reason"]} after {r["steps"]}; 670 now {dr.s16(G+670)}, level {dr.s16(G+662)}')
    dr.rpc('render', path=os.path.join(OUTDIR, f'rating_acc{acc}.png'))
dr.close()
