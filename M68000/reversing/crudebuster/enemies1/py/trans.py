"""State-transition census per (type, variant) from enemylog.txt files.  usage: trans.py log... 
A record instance is a slot's run of frames with the same type & active bit (a new instance starts when the slot goes inactive or the type changes
or x jumps are ignored).  Prints per type: instances, initial +5 (health) at first frame, transitions of +3 with counts."""
import sys, collections
from loglib import frames, w, b
inst = collections.defaultdict(lambda: dict(n=0, hp0=collections.Counter(), tr=collections.Counter(), st=collections.Counter(), var=collections.Counter()))
for path in sys.argv[1:]:
    prev = {}
    for fr in frames(path):
        for s, r in fr["R"].items():
            t = r[2]; D = inst[t]
            p = prev.get(s)
            if p is None or p[2] != t:
                D["n"] += 1; D["hp0"][r[5]] += 1; D["var"][r[16]] += 1
            else:
                if p[3] != r[3]: D["tr"][(p[3], r[3])] += 1
            D["st"][r[3]] += 1
        prev = {s: r for s, r in fr["R"].items()}
for t in sorted(inst):
    D = inst[t]
    print("type %d: instances %d variants %s first-frame +5 %s" % (t, D["n"], dict(D["var"]), dict(D["hp0"])))
    print("   frames in state:", " ".join("%x:%d" % (k, v) for k, v in sorted(D["st"].items())))
    print("   transitions:", " ".join("%x>%x:%d" % (a, c, n) for (a, c), n in sorted(D["tr"].items())))
