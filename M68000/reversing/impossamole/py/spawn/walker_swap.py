"""What separates the two snakes (types 126 `$015c7a` and 127 `$015c82`): handler-swap experiments.

    ATARI_NOTRACE=1 uv run python walker_swap.py

126 calls `$013270` (walk; when the probe below the box centre finds no ground, start falling at twice the speed, land, go on;
turn only at walls `$0136a8`), 127 calls `$0131c8` (turn at the screen edges x < $20 / x > $108 (`$013870`), at walls, and
at ledges: no ground under the leading edge). To show the difference on identical terrain the handler pointer 86(A0) of a live
walker is POKED (labelled) to the other handler:
  A. pass99/cyc0.snap slot 8 (a type 112 plant, `$0131c8` walker patrolling x 112..190 on a platform): natural run, then
     with 86(A0) = `$015c7a`. Natural: it turns at the platform ends. Swapped: it walks off the end and falls.
  B. pass103/room160.snap slot 7 (type 127 snake, turns at x = 266 > $108): natural, then with 86(A0) = `$015c7a`: it walks on
     to the despawn line (x > $130).
Prints, for each run, the x and y extremes reached and whether the object fell (y grew).
"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from replx import Repl
from trace_frames import trace


def run(snap, slot, handler, frames):
    with Repl(snap) as r:
        r.run('w bb74 12120300')
        o = r.obj(slot)
        if handler:
            r.poke(o['addr'] + 86, handler.to_bytes(4, 'big'))
        tr = trace(r, [slot], frames)
    live = [t[slot] for t in tr if t[slot]['tw']]
    return min(o['x'] for o in live), max(o['x'] for o in live), min(o['y'] for o in live), max(o['y'] for o in live), len(live)


P = 'scratchpad/impossamole/'
for label, snap, slot, frames in (('A plant on a platform', P + 'pass99/cyc0.snap', 8, 90), ('B snake at the screen edge', P + 'pass103/room160.snap', 7, 120)):
    for hname, h in (('own handler', None), ('86(A0) = $015c7a (126: walk off ledges, no edge turn)', 0x15c7a)):
        x0, x1, y0, y1, n = run(snap, slot, h, frames)
        print(f'{label}, {hname}: x {x0}..{x1}, y {y0}..{y1}, alive {n}/{frames} frames')
