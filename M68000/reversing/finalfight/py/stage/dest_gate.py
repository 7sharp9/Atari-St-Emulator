#!/usr/bin/env python3
"""dest_gate.py <poolrec.bin> [<slot>] ... : kind 3 destination rule (ai.md, "Kind 3", `$2e3f6`).

For every frame where pool-2 record <slot> (default 5) changes its destination word +132, the new value must equal player 1's x plus the offset +138 ($50 or $80)
when the side byte +137 is 1, minus it when 0 (the player moves 2 px a frame, so +-2 is allowed); also counts the destinations left of the camera window
(x < 1042(A5)), which the routine never tests (`$2e55a` calls only the terrain probe `$7fac`).
Input: a `py/ai_kind0/poolrec.lua` dump, e.g. from the stage 2 area 0 stall state:
  FF_SECONDS=2000 FF_REC_LO=46101 FF_REC_HI=46500 py/ai_kind0/run_ai.sh rec st1 sb_stall2 46500 ""     (sb_stall2: py/stage/README.md)
"""
import os, sys
here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(here, '..', 'ai_kind0'))
import rec

args = sys.argv[1:]
slot = int(args.pop(), 10) if args and args[-1].isdigit() and len(args[-1]) < 3 else 5
tot = ok = off = 0
for path in args:
    prev = None
    for fr in rec.load(path):
        r = fr.p2[slot]
        d, side, offs = rec.u16(r, 132), r[137], rec.u16(r, 138)
        px = rec.u16(fr.pl[0], 6)
        if prev is not None and d != prev:
            tot += 1
            exp = px + offs if side else px - offs
            if abs(d - exp) <= 2:
                ok += 1
            if d < fr.a(1042, 2):
                off += 1
        prev = d
print('destination changes', tot, 'equal player x +/- offset by side byte', ok, 'destinations left of the camera', off)
sys.exit(0 if tot and ok == tot else 1)
