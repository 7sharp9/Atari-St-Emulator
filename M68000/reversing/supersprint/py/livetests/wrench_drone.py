"""wrench_drone.py - do drones pick up wrenches (-3954[3] increments)?  From data/wr_base.snap teleport drone slot 3 (and, as the positive
control, the human slot 1) onto a grid of positions around the wrench cell (screen-px offsets dx,dy in -12..12 step 4 from the cell
origin, via Q -3738/-3746 and previous position -3786/-3794; Q = 8 x screen px) and run 3 frames.  Counts runs in which the car's counter went up by 1."""
from lt import *
base = os.path.join(DATA, 'wr_base.snap')
hits = {1: [], 3: []}
tot = 0
for car in (1, 3):
    for dx in range(-12, 13, 4):
        for dy in range(-12, 13, 4):
            r = Repl2(base)
            col, row = r.a4w(-1852, 1)[0], r.a4w(-1854, 1)[0]
            b = r.a4w(-3954, 4)[car]
            X, Y = (col * 8 + dx) * 8, (row * 8 + dy) * 8
            setwords(r, {A4 + o + 2 * car: v for o, v in ((-3786, X), (-3738, X), (-3794, Y), (-3746, Y))})
            for _ in range(3): r.cmd('s 12000')
            a = r.a4w(-3954, 4)[car]
            if a != b: hits[car].append((dx, dy, a - b))
            r.close()
    print('car', car, 'positions tried 49, pickups:', len(hits[car]), hits[car][:10], flush=True)
