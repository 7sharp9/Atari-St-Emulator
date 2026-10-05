"""Compact view of a lab/boss log: state timeline of every pool A record (type, state, hp, x-P1x, y), P1 hp drops, and flag changes ($80040/$80041/$80400/$81e03).
usage: bosslog.py <enemylog.txt> [maxlines] [slot-type filter ...]"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from loglib import frames, w
def sd(a, b): return (a - b + 32768) % 65536 - 32768
def main(path, maxl=120, types=None):
    prev = {}; flags = None; hp = None; n = 0
    for fr in frames(path):
        P = fr["P"]
        if P is None: continue
        f = fr["f"]
        fl = (fr["f40"], fr["f41"])
        l2 = None
        if flags is not None and fl != flags:
            print("%6d FLAGS $80040=%02x $80041=%02x" % (f, fl[0], fl[1])); n += 1
        flags = fl
        if hp is not None and P[0x13] < hp: print("%6d P1 hp %d -> %d  %s" % (f, hp, P[0x13], [(r[2], r[3], r[20]) for r in fr["R"].values()])); n += 1
        hp = P[0x13]
        for i, r in fr["R"].items():
            if types and r[2] not in types: continue
            k = (r[2], r[3])
            if prev.get(i) != k:
                print("%6d slot%2d type %2d var %d state %2x hp %3d dir %d dx %+5d y %04x +53=%02x +51=%02x" % (f, i, r[2], r[16], r[3], r[5], r[4], sd(w(r, 8), w(P, 8)), w(r, 12), r[53], r[51])); n += 1
                prev[i] = k
        for i in list(prev):
            if i not in fr["R"]:
                if not types or prev[i][0] in types: print("%6d slot%2d type %2d GONE" % (f, i, prev[i][0])); n += 1
                del prev[i]
        if n > maxl: print("..."); break
if __name__ == "__main__":
    main(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 120, set(int(x) for x in sys.argv[3:]) or None)
