"""Log the boss's projectiles (type 139 `$014790`, type 140 `$016184`) frame by frame while the hero idles (no input, no poke).

    ATARI_NOTRACE=1 uv run python reversing/impossamole/py/boss/shot140_probe.py [snap]

Default start: `agents/unpoked/hop4/none/seg5_pit_exit.snap` (boss room, hero landed at x=32). Every 6,000 steps (a quarter frame, 24,000 steps per frame)
it reads slots 8-15 and prints, per shot, its position each time it changes (`(kilosteps, x, y)`). Expect for the first 140 (slot 12): spawn (231, 121) at
about 642k steps, x falling 1 px per frame, y 121 to 108 in 8 frames, then 109, 110, 111, 112, 114, 116, 118, 121, 124, 128 ... 164 on frame 27.
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'route'))
from route_driver import *

snap = sys.argv[1] if len(sys.argv) > 1 else 'scratchpad/impossamole/agents/unpoked/hop4/none/seg5_pit_exit.snap'
d = Driver(snap, 'scratchpad/impossamole/agents/unpoked/boss/shot140_probe', tick=8000, hp_floor=-1)
seen = {}
for _ in range(400):
    d.step(6000)
    s = d.read()
    for o in d.objects():
        h = int.from_bytes(o['raw'][86:90], 'big')
        if o['type'] and o['slot'] >= 8 and h in (0x16184, 0x14790):
            seen.setdefault((o['slot'], h), []).append((d.total_steps, o['x'], o['y']))
    if s.hp <= 2:
        break
for k, v in seen.items():
    moved = [v[0]] + [b for a, b in zip(v, v[1:]) if (a[1], a[2]) != (b[1], b[2])]
    print(f'slot {k[0]} handler {k[1]:#x}:', [(t // 1000, x, y) for t, x, y in moved][:40])
d.close()
