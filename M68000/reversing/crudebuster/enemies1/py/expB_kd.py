"""Experiment B, classification of every hit poke: ignored (hp unchanged), kill (record gone / hp 0 before it returns to state 6/7), stun (back in state 6 within
20 frames, no vertical excursion) or knock-down (longer, vertical excursion).  Grouped by (type,var,value) and the state class at the poke.
usage: expB_kd.py [type]"""
import sys, os, glob, collections
sys.path.insert(0, os.path.dirname(__file__))
from loglib import frames, w
def sd(a, b): return (a - b + 32768) % 65536 - 32768
AIR = {9, 0xa, 0xb, 0xc, 0xe, 0x10, 0x11, 0x12, 0x13, 0x14, 0x15, 0x16}
def classify(path):
    fr = list(frames(path)); byf = {f["f"]: f for f in fr}; off = fr[0]["f"]; res = []
    for l in open(path):
        if not (l.startswith("E ") and " hit " in l): continue
        t = l.split(); h = int(t[1]) + off; V = int(t[6], 16)
        a = byf.get(h)
        if a is None or 0 not in a["R"]: res.append((V, None, "no record")); continue
        r0 = a["R"][0]; st0 = r0[3]; hp0 = r0[5]; y0 = w(r0, 12)
        ymax = 0; outcome = None; T = None
        hp1 = None
        for k in range(1, 140):
            b = byf.get(h + k)
            if b is None: break
            if 0 not in b["R"]:
                outcome = "kill"; T = k; break
            r = b["R"][0]
            if k <= 3: hp1 = r[5]
            ymax = max(ymax, abs(sd(w(r, 12), y0)))
            if k > 3 and hp1 is not None and hp1 == hp0 and r[3] == st0 and k <= 6:
                outcome = "ignored"; T = k; break
            if k >= 3 and r[3] in (6, 7) and r[3] != st0 or (k >= 3 and r[3] == 6):
                outcome = ("stun" if k <= 20 and ymax <= 2 else "knock"); T = k; break
        res.append((V, st0, outcome, T, ymax, hp0, hp1))
    return res
if __name__ == "__main__":
    only = int(sys.argv[1]) if len(sys.argv) > 1 else None
    agg = collections.defaultdict(collections.Counter)
    for d in sorted(glob.glob("out/expB/*"), key=lambda s: (int(os.path.basename(s).split("_")[0]), s)):
        tag = os.path.basename(d); ty = int(tag.split("_")[0])
        if only is not None and ty != only: continue
        p = os.path.join(d, "enemylog.txt")
        if not os.path.exists(p): continue
        for r in classify(p):
            if r[1] is None: continue
            V, st0, outc, T, ymax, hp0, hp1 = r
            cls = "air" if st0 in AIR else ("hurt/down" if st0 in (1, 2, 4, 5) else "ground")
            agg[(ty, tag.split("_")[1], cls)][(outc, "V%02x" % V, "dhp=%s" % (hp0 - hp1 if hp1 is not None and hp1 <= hp0 else "?"))] += 1
    for k in sorted(agg):
        print(k, dict(agg[k]))
