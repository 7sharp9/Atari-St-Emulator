"""Live check of the monkey's death drop (type 110 -> kind-3 object type 52, handler `$0147e6`).

    ATARI_NOTRACE=1 uv run python monkey_drop.py

`$013a9c` returns carry when the shot leaves hp <= 0; `$015938: bcs $015a02` then spawns object type `$34` (52) at
(x + 4, y + 8) through `$01366e`. Shots are POKED onto the monkey (labelled, as in immune_shot.py; weapon `$bb72` poked to 3) until it dies; then the
drop is followed, and the hero is POKED onto it to see the pickup (`$013044`: sound `$19`, `$bb73` += 25, capped `$fa`).
"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from replx import Repl
from trace_frames import trace

with Repl('scratchpad/impossamole/gameplay_explore/ru_step4M.snap') as r:
    r.run('w bb74 12120300')
    r.poke(0xbb72, b'\x03')      # weapon 3 (damage 3 per shot; the snapshot has weapon 1): labelled
    print('bb73 before the fight:', r.mem(0xbb73, 1).hex())
    r.run('s 1', 'bp b4de 200000')
    for shot in range(1, 16):
        for _ in range(6):
            if r.mem(0x227f3, 1)[0] < 3:
                break
            r.run('s 1', 'bp b4de 200000')
        m = r.obj(9)
        r.run('w bb74 12120300', 'kbd ff', 'kbd 80', 's 30000', 'kbd ff', 'kbd 00', 's 2000')
        m = r.obj(9)
        r.run(f"w 1a9ac {m['x'] & 0xffff:04x}{m['y'] & 0xffff:04x}", 's 30000')
        m = r.obj(9)
        print(f"shot {shot}: monkey hp {m['hp']} 101={m['dead']} 102={m['inv']} anim ${m['anim']:05x} y {m['y']}")
        if m['dead']:
            break
    print('bb73 before pickup:', r.mem(0xbb73, 1).hex())
    drop = None
    for s in range(12, 16):
        o = r.obj(s)
        if o['tw']:
            drop = o
            print(f"drop slot {s}: tw {o['tw']} x {o['x']} y {o['y']} frame {o['frame']} anim ${o['anim']:05x} handler {int.from_bytes(o['raw'][86:90], 'big'):#x} dmg {o['dmg']} hp {o['hp']}")
    if drop:
        s = (drop['addr'] - 0x1a2ea) // 108
        tr = trace(r, [s], 30)
        print('drop y over 30 frames:', [t[s]['y'] for t in tr][:30])
        o = r.obj(s)
        r.poke(0x1a574, (o['x'] & 0xffff).to_bytes(2, 'big') + (o['y'] & 0xffff).to_bytes(2, 'big'))
        r.run('s 60000')
        print('after hero poked onto the drop: slot tw', r.obj(s)['tw'], ' bb73:', r.mem(0xbb73, 1).hex())
