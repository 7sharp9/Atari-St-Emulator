"""Live check of the crocodile (type 130, `$015d26`) as a rideable platform (README "Spawn types", item c).

    ATARI_NOTRACE=1 uv run python croc_ride.py

`$015d26` calls `$e5fe` (the moving-platform routine) only while the crocodile's frame is `$8c` (140) or `$90` (144), its
jaws-shut back; on any other frame, if the hero is riding it (`$227f9` = 1, `$227a0` = this object) the hero is dropped
(`clr.w 16(A1)`, `jsr $cb2e`). Contact damage is the descriptor's 0. From gameplay_explore/ru_step8M.snap (crocodile in
slot 8): run to a frame of the shut back, POKE the hero to fall onto it (state `$227f3` = 3, feet 4 px above its top: labelled),
then follow the hero for 150 frames printing, on each change, the crocodile frame, `$227f9`, the hero's offset from the
crocodile and health. Health is poked full each frame only if it drops (it should not: damage 0).
"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from replx import Repl
from trace_frames import trace

snap = 'scratchpad/impossamole/gameplay_explore/ru_step8M.snap'
with Repl(snap) as r:
    r.run('w bb74 12120300')
    for _ in range(80):
        r.run('s 1', 'bp b4de 200000')
        o = r.obj(8)
        if o['frame'] == 144 and o['tw']:
            break
    print('croc at', o['x'], o['y'], 'frame', o['frame'], 'anim', hex(o['anim']))
    hy = o['y'] + 10 - 0x14 - 4
    hx = o['x'] + 8
    r.poke(0x1a574, (hx & 0xffff).to_bytes(2, 'big') + (hy & 0xffff).to_bytes(2, 'big'))
    r.poke(0x227f3, b'\x03')        # hero state 3 (falling)
    rows = []
    tr = trace(r, [8, 6], 150, extra=lambda r: (r.mem(0x227f9, 1)[0], int.from_bytes(r.mem(0x227a0, 4), 'big'), r.mem(0xbb74, 1)[0], r.mem(0x227f3, 1)[0]))
    last = None
    for i, t in enumerate(tr):
        c, h = t[8], t[6]
        ride, ptr, hp, st = t['extra']
        key = (c['frame'], ride, st)
        if key != last:
            print(f"f{i:3d} croc frame {c['frame']} ({'shut back' if c['frame'] in (140, 144) else 'other'}) riding {ride} target ${ptr:05x} hero state {st} hero-croc dx {h['x'] - c['x']} dy {h['y'] - c['y']} hp {hp}")
            last = key
