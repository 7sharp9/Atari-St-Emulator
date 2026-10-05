import sys, os, glob
sys.path.insert(0, os.path.dirname(__file__))
from labana import timeline, hpdrops
for d in sorted(glob.glob("out/expA/*"), key=lambda s: (int(s.split("/")[-1].split("_")[0]), s)):
    tag = os.path.basename(d); p = os.path.join(d, "enemylog.txt")
    if not os.path.exists(p): continue
    tl = timeline(p)
    seq = []
    for t in tl:
        if len(t) == 4: seq.append("gone@%d" % t[0])
        else: seq.append("%x@%d(dx%+d,dy%+d)" % (t[3], t[0] - 1005, t[5], t[6]))
    dr = hpdrops(p)
    print(tag, " ".join(seq[:26]))
    print("     drops:", " ".join("%d:-%d(st%x,f%d,dx%+d)" % (f - 1005, dmg, es[0][2], es[0][3], es[0][4]) if es else "%d:-%d(none)" % (f - 1005, dmg) for f, dmg, es in dr[:14]))
