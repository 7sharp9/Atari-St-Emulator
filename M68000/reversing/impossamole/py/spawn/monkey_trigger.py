"""Live check of the monkey's ambush trigger and fall (type 110, `$015934`).

    ATARI_NOTRACE=1 uv run python monkey_trigger.py

From gameplay_explore/ru_step4M.snap (the monkey, slot 9, is already falling): the monkey is POKED back to its pre-trigger
state (78 = 0, animation `$21fd6`, frame index 0; labelled). With the hero outside the `$e5a0` box (D0 = 0, D1 = $40,
D2 = 0, D3 = $40: hero-minus-monkey dx in (-30, 22), dy in (-24, 152)) it must stay put; with the hero poked inside it must
switch to state 1 (animation `$21fe0`, frame 134) and fall along the script (speeds 1,1,1,1,2,2,2,3,3,4,4.. down) until
`$01359c` sees ground, then state 2 (`$21fe4`, frame 135/136 loop) and throw at 82 = 16, 32, 48 (`$015a14`).
"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from replx import Repl
from trace_frames import trace

with Repl('scratchpad/impossamole/gameplay_explore/ru_step4M.snap') as r:
    r.run('w bb74 12120300')
    o = r.obj(9)
    r.poke(o['addr'] + 78, b'\0')
    r.poke(o['addr'] + 82, (0).to_bytes(2, 'big'))
    r.poke(o['addr'] + 22, (0x21fd6).to_bytes(4, 'big') + (0).to_bytes(2, 'big'))
    r.poke(o['addr'] + 16, bytes(4))      # 16/18(A0) := 0: the fall left vy = 2..4 behind
    print('monkey before', o['x'], o['y'])
    # hero far to the right of the box
    r.poke(0x1a574, ((o['x'] + 60) & 0xffff).to_bytes(2, 'big') + ((o['y'] + 40) & 0xffff).to_bytes(2, 'big'))
    tr = trace(r, [9], 12)
    print('hero outside the box, 12 frames: 78 =', sorted({t[9]['b78'] for t in tr}), 'y =', sorted({t[9]['y'] for t in tr}))
    o = r.obj(9)
    r.poke(0x1a574, ((o['x'] - 4) & 0xffff).to_bytes(2, 'big') + ((o['y'] + 40) & 0xffff).to_bytes(2, 'big'))
    tr = trace(r, [9], 40)
    for i, t in enumerate(tr):
        m = t[9]
        if i < 14 or i in (14, 15, 16):
            print(f"  f{i:2d} 78={m['b78']} y {m['y']} v=({m['w16']},{m['w18']}) frame {m['frame']} anim ${m['anim']:05x}")
