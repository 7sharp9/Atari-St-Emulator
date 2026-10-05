"""Analyse a lab log (lua/lab.lua).  functions: timeline(path), hpdrops(path).  usage: labana.py <enemylog.txt> [timeline|drops]"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from loglib import frames, w
def sdiff(a, b): return (a - b + 32768) % 65536 - 32768
def timeline(path, slot=None, limit=60):
    out = []; prev = {}
    for fr in frames(path):
        P = fr["P"]
        if P is None: continue
        for i, r in fr["R"].items():
            if slot is not None and i != slot: continue
            k = (i, r[2], r[3])
            if prev.get(i) != k:
                out.append((fr["f"], i, r[2], r[3], r[4], sdiff(w(r, 8), w(P, 8)), sdiff(w(r, 12), w(P, 12)), r[5], r[17], r[51], r[53]))
                prev[i] = k
        for i in list(prev):
            if i not in fr["R"]: out.append((fr["f"], i, prev[i][1], "gone")); del prev[i]
    return out
def hpdrops(path):
    out = []; prevhp = None
    for fr in frames(path):
        P = fr["P"]
        if P is None: continue
        hp = P[0x13]
        if prevhp is not None and hp < prevhp:
            es = [(i, r[2], r[3], r[20], sdiff(w(r, 8), w(P, 8)), sdiff(w(r, 12), w(P, 12)), r[6]) for i, r in fr["R"].items()]
            out.append((fr["f"], prevhp - hp, es))
        prevhp = hp
    return out
if __name__ == "__main__":
    p = sys.argv[1]; mode = sys.argv[2] if len(sys.argv) > 2 else "timeline"
    if mode == "timeline":
        for t in timeline(p): print(t)
    else:
        for t in hpdrops(p): print(t)
