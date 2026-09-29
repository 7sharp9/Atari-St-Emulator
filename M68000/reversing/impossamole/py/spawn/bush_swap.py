"""Handler-swap check of the leaf-bush handlers (types 131/132, `$015d82`/`$015d9c`), which have no live object in any snapshot.

    ATARI_NOTRACE=1 uv run python bush_swap.py

The plant in pass99/cyc0.snap slot 8 (type 112, patrols x 112..190 on a platform) has its handler pointer 86(A0) POKED to
the bush handler (labelled: this shows what the handler code does, not that a bush exists there). `$015d9c` (type 132)
freezes the object (100(A0) = 2 each frame) until `$e5a0` (D0 = $20, D1 = 0, D2 = -16, D3 = 0) finds the hero, then sets
78(A0) = 1 and patrols with `$0131c8`. Phase 1: hero in place, 40 frames (hero-minus-object dx = 52, outside the box
(-78, 38)): the object must not move. Phase 2: hero poked to dx = 10: it must start walking within a frame.
`$015d82` (type 131) has no trigger: it walks at once and pauses 48-96 frames now and then (`$13988`, mask $3f).
"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from replx import Repl
from trace_frames import trace


def run(handler, hero_poke, frames=40):
    with Repl('scratchpad/impossamole/pass99/cyc0.snap') as r:
        r.run('w bb74 12120300')
        r.poke(0x1a64a + 86, handler.to_bytes(4, 'big'))
        r.poke(0x1a64a + 78, b'\0')
        if hero_poke:
            o = r.obj(8)
            r.poke(0x1a574, ((o['x'] + hero_poke[0]) & 0xffff).to_bytes(2, 'big') + ((o['y'] + hero_poke[1]) & 0xffff).to_bytes(2, 'big'))
        tr = trace(r, [8], frames)
    xs = [t[8]['x'] for t in tr]
    return xs, [t[8]['b78'] for t in tr], [t[8]['st'] for t in tr]


for label, h, poke in (('132 handler, hero out of the trigger box', 0x15d9c, None),
                       ('132 handler, hero poked into the box (dx +10, dy 0)', 0x15d9c, (10, 0)),
                       ('131 handler (no trigger)', 0x15d82, None)):
    xs, b78, st = run(h, poke)
    print(f'{label}: x {xs[0]} -> {xs[-1]}, moved {sum(1 for a, b in zip(xs, xs[1:]) if a != b)} of {len(xs) - 1} frames; 78 = {sorted(set(b78))}; frozen frames {sum(1 for s in st if s)}')
