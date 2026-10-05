#!/usr/bin/env python3
"""mkplan.py "<spec>" > plan.lua     spec: ';'-separated items  <frame> <btn[+btn...]> <hold>
   btn: up down left right b1 b2 b3 p2up p2down p2left p2right p2b1 p2b2 p2b3 start1 start2 coin
   e.g.  "960 b1 6; 1000 right+b1 10"  -> sets each field to 1 at frame and to 0 at frame+hold."""
import sys
ev = []
for it in sys.argv[1].split(";"):
    it = it.strip()
    if not it: continue
    f, btns, hold = it.split(); f = int(f); hold = int(hold)
    for b in btns.split("+"):
        ev.append((f, b, 1)); ev.append((f + hold, b, 0))
ev.sort(key=lambda e: (e[0], e[2]))   # releases (0) before presses (1) at the same frame
print("return {")
for f, b, v in ev: print('  { %d, "%s", %d },' % (f, b, v))
print("}")
