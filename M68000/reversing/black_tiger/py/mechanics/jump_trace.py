"""Live per-tick (x,y) trace of the hero for scripted joystick sequences, from play_start.snap, using a watch on $1f014..$1f017
(x written at $e61c, y at $e544 once per game tick).  Compare against player_model: the vertical series must equal the jump/fall table.
Usage: jump_trace.py            prints three scenarios: straight jump (up), diagonal jump (up+right), delayed-right jump (up, then right after ~3 ticks)."""
import os, re, sys
sys.path.insert(0, os.path.dirname(__file__))
import btlib as b
snap = os.path.join(b.WORK, "play_start.snap")
def trace(script, total):
    lines = ["watch 1f014 4"] + script + ["s %d" % total]
    out = b.repl(snap, lines)
    ticks = []; cur = {}
    for l in out.splitlines():
        m = re.match(r"WATCH: step=(\d+) pc=\$([0-9a-f]+) WriteWord \$0001f01([46]) <- \$([0-9a-f]+)", l)
        if not m: continue
        step, pc, which, val = int(m.group(1)), m.group(2), m.group(3), int(m.group(4), 16)
        if pc.endswith("e544"): cur["y"] = val
        if pc.endswith("e61c"):
            cur["x"] = val; cur["step"] = step; ticks.append(cur); cur = {}
    return ticks
def show(name, ticks):
    ys = [t["y"] for t in ticks]; xs = [t["x"] for t in ticks]
    dy = [b2 - a for a, b2 in zip(ys, ys[1:])]
    print(name); print("  dy per tick:", dy); print("  x per tick :", xs)
    return ys
RISE = [15, 11, 7, 4, 2, 1]; FALL = [0, 1, 2, 4, 7, 11, 15]
y = trace(["kbd ff 01", "s 80000", "kbd ff 00"], 1200000); ys = show("straight jump (up held ~1 tick, released)", y)
dy = [b2 - a for a, b2 in zip([t["y"] for t in y], [t["y"] for t in y][1:])]
exp = [-v for v in RISE] + FALL
i = next(k for k, d in enumerate(dy) if d)
exp = [-v for v in RISE] + [v for v in FALL[1:]]       # the +0 fall step shares the tick of the last rise step
print("  matches table sequence (rise -15,-11,-7,-4,-2,-1 then fall +1,+2,+4,+7,+11,+15):", dy[i:i + len(exp)] == exp)
y = trace(["kbd ff 09", "s 80000", "kbd ff 00"], 1200000); show("diagonal jump (up+right pressed together)", y)
y = trace(["kbd ff 01", "s 80000", "kbd ff 00", "s 150000", "kbd ff 08", "s 150000", "kbd ff 00"], 1500000); show("delayed right (up, release, then right alone ~3 ticks later: moves at the top of the arc)", y)
