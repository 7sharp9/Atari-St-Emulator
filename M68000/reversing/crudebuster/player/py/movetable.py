"""movetable.py: frame data of the player's moves from the logs of the standard runs (frame 0 = the frame the game first sees the sub-action byte +5 change).
   usage: movetable.py <moves1 reclog> <moves2 reclog> <dash reclog> <weapon reclog> <grab2 reclog>"""
import sys
def load(fn):
    rows = {}
    for ln in open(fn):
        p = ln.split(); rows[int(p[0])] = bytes.fromhex(p[1])
    return rows
def seg(rows, start, sub, maxlen=80):
    """first frame >= start where +5 == sub; returns (f0, f_end_exclusive, active frame offsets)"""
    f0 = next(f for f in range(start, start + 400) if rows[f][5] == sub)
    f = f0
    while f in rows and rows[f][5] == sub and f - f0 < maxlen: f += 1
    act = [i for i in range(f - f0) if rows[f0 + i][28]]
    return f0, f, act
def rng(a):
    if not a: return "none"
    out = []; s = p = a[0]
    for x in a[1:]:
        if x == p + 1: p = x; continue
        out.append("%d-%d" % (s, p) if s != p else str(s)); s = p = x
    out.append("%d-%d" % (s, p) if s != p else str(s))
    return ",".join(out)
m1, m2, dash, wp, g2 = (load(a) for a in sys.argv[1:6])
rows = []
def add(name, rws, start, sub, note=""):
    f0, f1, act = seg(rws, start, sub)
    rows.append((name, f1 - f0, rng(act), note))
add("jab, one tap (stand, pose 0)", m1, 1030, 2) if False else None
f0, f1, act = seg(m1, 1120, 3); rows.append(("jump, neutral (pose 5)", f1 - f0, rng(act), "airborne frames 1..32"))
f0, f1, act = seg(m1, 1220, 3); rows.append(("jump, forward (pose 6)", f1 - f0, rng(act), "dx 1.75/frame"))
f0, f1, act = seg(m1, 1320, 3); rows.append(("jump + b1 pressed at air frame 15 (kick, +6 = 1)", f1 - f0, rng(act), "active from the press until landing"))
f0, f1, act = seg(m1, 1420, 1); rows.append(("grab, empty hands (b3, pose 0, +27 = 4)", f1 - f0, rng(act), "pickup test on frames 8..15"))
f0, f1, act = seg(m2, 1000, 2); rows.append(("jab, b1+b2 held (stand)", f1 - f0, rng(act), ""))
f0, f1, act = seg(m2, 1595, 2); rows.append(("walking jab (right+b1, pose 3)", f1 - f0, rng(act), "x frozen during the move"))
f0, f1, act = seg(m2, 1725, 7); n = f1 - f0
rows.append(("turn-around attack, hop kick (+5 = 7, pose 12)", n, rng(act), "then +5 = 6 (fall, pose $10) until landing"))
f0, f1, act = seg(dash, 1196, 5); rows.append(("roll (down-diagonal + b2, +5 = 5, pose 4)", f1 - f0, rng(act), "x +-2 px/frame, no attack box"))
f0, f1, act = seg(wp, 1095, 2); rows.append(("swing carried weapon (b1, +27 = 3)", f1 - f0, rng(act), ""))
f0, f1, act = seg(g2, 1630, 4); rows.append(("throw (b3 while carrying, +5 = 4)", f1 - f0, rng(act), "object released on frame 1"))
print("%-52s %5s  %-10s %s" % ("move (frame 0 = frame +5 first changes)", "total", "active", "note"))
for r in rows: print("%-52s %5d  %-10s %s" % r)
