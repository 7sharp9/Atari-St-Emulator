"""Live check of the stone slab (type 109, `$013cb4`): it falls in 11 frames, and where it stops the hero in its box is hurt.

    ATARI_NOTRACE=1 uv run python slab_crush.py

pass103/live_c20.snap slot 8 (slab at (240,40), 25-frame rest, then a thrust of 24 px in 11 frames, then a retract). The
hero is POKED to the slab's x and 4 px below its top before every frame (labelled) and its health `$bb74`, state `$227f3`
and the slab's y and phase are printed on change. `$013e40..$013eda`: at the end of the thrust (`21(A1)` of the child
goes 0) the slab plays sound `$1d`, and if the hero's box touches it: sound 8, `$227f6 = 2` (damage 2), `$227f8 = $32`, hero
state `$227f3 := 0` and the hurt animation `$218ae`/`$218b2`.
"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from replx import Repl

with Repl('scratchpad/impossamole/pass103/live_c20.snap') as r:
    for sl in (7, 9):      # bees of the snapshot removed (type word := 0, labelled)
        r.poke(0x1a2ea + sl * 108, b'\0\0')
    last = None
    for f in range(60):
        s = r.obj(8)
        r.poke(0x1a574, (s['x'] & 0xffff).to_bytes(2, 'big') + ((s['y'] + 4) & 0xffff).to_bytes(2, 'big'))
        r.run('s 1', 'bp b4de 200000')
        s = r.obj(8)
        c = r.obj(12)
        hp, st = r.mem(0xbb74, 1)[0], r.mem(0x227f3, 1)[0]
        k = (s['b78'], c['b21'] if c['tw'] else None, hp, st)
        if k != last:
            print(f"f{f:2d} slab y {s['y']} 78={s['b78']} child(21)={c['b21'] if c['tw'] else '-'} hero health {hp} state {st} $227f6 {r.mem(0x227f6, 1).hex()}")
            last = k
