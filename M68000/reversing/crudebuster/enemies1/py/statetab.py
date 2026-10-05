"""Per-state table from a lab log, for one slot (default 0): entries, entry dx range (enemy x - P1 x), duration (median frames), P1 hp drops while in the state
(amount: count).  usage: statetab.py <enemylog.txt> [slot] [type]"""
import sys, os, collections, statistics
sys.path.insert(0, os.path.dirname(__file__))
from loglib import frames, w
def sd(a, b): return (a - b + 32768) % 65536 - 32768
def table(path, slot=0, typ=None):
    ent = collections.defaultdict(list); dur = collections.defaultdict(list); drops = collections.defaultdict(collections.Counter)
    prev = None; start = None; hp = None; seen = set()
    for fr in frames(path):
        P = fr["P"]
        if P is None: continue
        r = fr["R"].get(slot)
        if hp is not None and P[0x13] < hp and prev is not None:
            drops[prev[1]][hp - P[0x13]] += 1
        hp = P[0x13]
        if r is None or (typ is not None and r[2] != typ):
            if prev is not None: dur[prev[1]].append(fr["f"] - start)
            prev = None; continue
        if prev is None or prev[1] != r[3] or prev[0] != r[2]:
            if prev is not None: dur[prev[1]].append(fr["f"] - start)
            ent[r[3]].append(sd(w(r, 8), w(P, 8))); start = fr["f"]
            prev = (r[2], r[3])
    return ent, dur, drops
def show(path, slot=0, typ=None):
    ent, dur, drops = table(path, slot, typ)
    for s in sorted(ent):
        e = ent[s]; d = dur[s]
        print("  state %2x: entries %3d  dx %+d..%+d  dur median %s  hp drops %s" % (s, len(e), min(e), max(e), (int(statistics.median(d)) if d else "-"), dict(drops[s]) or "-"))
if __name__ == "__main__":
    show(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 0, int(sys.argv[3]) if len(sys.argv) > 3 else None)
