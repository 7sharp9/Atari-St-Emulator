"""Live check that a falling rock hurts the hero for its contact damage 2 and is destroyed by the contact (type 113, `$01439e`).

    ATARI_NOTRACE=1 uv run python rock_hit.py

`$01439e ... bsr $e80e; bne $143e0; bsr $13b4c`: on a contact with an unhurt hero the rock sets `$227f6 = 104(A0) = 2`
(hero damage, `$eb80` subtracts it from `$bb74`) and is killed at once (crumble animation `$22036`). From
pass103/live_c1.snap slot 7 (rock at (96,16)) the two bees of the snapshot are removed by poking their type words to 0
(labelled) so nothing else can hurt.
  Run 1: the hero is POKED (labelled) to (96,34) once and left to stand on the ground: the rock falls and dies on landing
         (`$013544`, the ground probe, runs before the contact test) and health does not change.
  Run 2: the hero is POKED to (96,26) before every frame (labelled: it stays in the rock's trigger box and path): the rock
         touches it, health drops by 2 and the rock crumbles at once.
"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from replx import Repl
from trace_frames import trace

SNAP = 'scratchpad/impossamole/pass103/live_c1.snap'


def start():
    r = Repl(SNAP)
    for sl in (8, 9):
        r.poke(0x1a2ea + sl * 108, b'\0\0')
    return r


def hero_at(r, y):
    r.poke(0x1a574, (96).to_bytes(2, 'big') + y.to_bytes(2, 'big'))


with start() as r:
    hero_at(r, 34)
    tr = trace(r, [7], 25, extra=lambda r: r.mem(0xbb74, 1)[0])
    print('run 1, hero standing on the ground: rock dead flag over the last 10 of 25 frames', [t[7]['dead'] for t in tr][-10:],
          '| health values seen', sorted({t['extra'] for t in tr}))

with start() as r:
    last = None
    for f in range(30):
        hero_at(r, 26)
        r.run('s 1', 'bp b4de 200000')
        rk, hp = r.obj(7), r.mem(0xbb74, 1)[0]
        k = (rk['dead'], hp, rk['anim'])
        if k != last:
            print(f"run 2 f{f:2d} rock y {rk['y']} dead {rk['dead']} anim ${rk['anim']:05x}  hero y {r.obj(6)['y']} health {hp}")
            last = k
