"""Experiment D: measured speeds.  From the expA lab logs: per (type,var,state) the per-frame change of the 32-bit x (+8..+11, 16.16 fixed) and y (+12..+15) while the
state is unchanged between two consecutive frames, reported as the modal |dx| and |dy| in px/frame with the count of frames that show it.
usage: expD.py   (reads out/expA/*)"""
import sys, os, glob, collections
sys.path.insert(0, os.path.dirname(__file__))
from loglib import frames, l
def s32(v): return v - (1 << 32) if v >= 1 << 31 else v
acc = collections.defaultdict(collections.Counter)
for d in glob.glob("out/expA/*"):
    tag = os.path.basename(d); t, v = int(tag.split("_")[0]), int(tag.split("_")[1])
    p = os.path.join(d, "enemylog.txt")
    if not os.path.exists(p): continue
    prev = None
    for fr in frames(p):
        r = fr["R"].get(0)
        if r is None: prev = None; continue
        if prev is not None and prev[3] == r[3] and prev[2] == r[2] and not (prev[0] & 0x01 and False):
            dx = s32(l(r, 8)) - s32(l(prev, 8)); dy = s32(l(r, 12)) - s32(l(prev, 12))
            acc[(t, v, r[3])][(abs(dx) / 65536.0, abs(dy) / 65536.0)] += 1
        prev = r
print("type var state : most common (|dx|,|dy|) px/frame (frames) ...")
for k in sorted(acc):
    c = acc[k]; tot = sum(c.values())
    print("%2d %d %2x : n=%d  " % (k[0], k[1], k[2], tot) + "  ".join("(%.3f,%.3f)x%d" % (a, b, n) for (a, b), n in c.most_common(3)))
