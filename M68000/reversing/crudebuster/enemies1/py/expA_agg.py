"""Aggregate experiment A over its four starting offsets per (type,var): per state the entries, |dx| at entry (min..max), median duration, P1 hp drops while in the state.
usage: expA_agg.py [type]"""
import sys, os, glob, collections, statistics
sys.path.insert(0, os.path.dirname(__file__))
from statetab import table
agg = {}
for d in sorted(glob.glob("out/expA/*")):
    tag = os.path.basename(d); t, v = int(tag.split("_")[0]), int(tag.split("_")[1])
    if len(sys.argv) > 1 and t != int(sys.argv[1]): continue
    p = os.path.join(d, "enemylog.txt")
    if not os.path.exists(p): continue
    ent, dur, drops = table(p, 0, t)
    A = agg.setdefault((t, v), dict(ent=collections.defaultdict(list), dur=collections.defaultdict(list), drops=collections.defaultdict(collections.Counter)))
    for s in ent: A["ent"][s] += [abs(x) for x in ent[s]]
    for s in dur: A["dur"][s] += dur[s]
    for s in drops: A["drops"][s].update(drops[s])
for (t, v), A in sorted(agg.items()):
    print("type %d var %d" % (t, v))
    for s in sorted(A["ent"]):
        e = A["ent"][s]; d = A["dur"][s]
        print("   state %2x  entries %3d  |dx| %3d..%3d  dur median %3s  P1 hp drops %s" % (s, len(e), min(e), max(e), int(statistics.median(d)) if d else "-", dict(A["drops"][s]) or "-"))
