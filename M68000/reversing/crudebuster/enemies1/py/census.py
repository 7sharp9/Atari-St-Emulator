"""Per-level census of the list A script (enemies, $6c000) against a natural bot run (lua/enemylog.lua log): which entry spawned when, at which scroll position,
in which order.  Matching: a record that becomes active in a frame with type/variant/x/y equal to the entry (the spawner copies these; the handler may move x within
the same frame, so x is matched within +-0x20 and y exactly or within 0x10).  usage: census.py <level> <enemylog.txt>"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from scripts import A, B
from loglib import frames, w
def census(level, path):
    ents = A[level]; used = [None] * len(ents); order = []
    prev = {}
    for fr in frames(path):
        for i, r in fr["R"].items():
            key = (i, r[2], r[16])
            if prev.get(i) != (r[2], r[16], r[0] & 0x80, r[3]) and (i not in prev):
                # newly active slot
                x, y = w(r, 8), w(r, 12)
                for k, e in enumerate(ents):
                    if used[k] is None and e["type"] == r[2] and e["var"] == r[16] and abs(e["x"] - x) <= 0x30 and abs(e["y"] - y) <= 0x20:
                        used[k] = (fr["f"], fr["sx"], x, y); order.append(k); break
                else: order.append(("extra", r[2], r[16], fr["f"], fr["sx"], x, y))
            prev[i] = (r[2], r[16], r[0] & 0x80, r[3])
        for i in list(prev):
            if i not in fr["R"]: del prev[i]
    return ents, used, order
if __name__ == "__main__":
    lv = int(sys.argv[1]); ents, used, order = census(lv, sys.argv[2])
    n = sum(1 for u in used if u)
    print("level %d: %d of %d list A entries seen spawning" % (lv, n, len(ents)))
    for k, (e, u) in enumerate(zip(ents, used)):
        print("%2d trig %04x type %2d var %d x %04x y %04x | %s" % (k, e["trig"], e["type"], e["var"], e["x"], e["y"], ("frame %d sx %04x" % (u[0], u[1])) if u else "not seen"))
    print("non-script records seen:", [o for o in order if isinstance(o, tuple)][:40])
