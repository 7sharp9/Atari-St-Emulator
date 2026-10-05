"""Summarise experiment B: for each hit poke, the reaction of enemy slot 0 (state sequence in the 4 frames after the poke, hp change)."""
import sys, os, glob, collections
sys.path.insert(0, os.path.dirname(__file__))
from loglib import frames, w
def analyse(path):
    fr = list(frames(path))
    byf = {f["f"]: f for f in fr}
    hits = []
    for l in open(path):
        if l.startswith("E ") and " hit " in l:
            t = l.split(); hits.append((int(t[1]), int(t[6], 16)))
    f0 = fr[0]["f"] if fr else 0
    res = []
    off = fr[0]["f"]  # E lines carry frames relative to the first logged frame (lab.lua r = f - f0)
    for h, V in hits:
        a = byf.get(h + off)
        if a is None or 0 not in a["R"]: res.append((h, V, "gone")); continue
        r0 = a["R"][0]
        seq = []
        for k in range(1, 6):
            b = byf.get(h + off + k)
            if b is None or 0 not in b["R"]: seq.append("x"); break
            seq.append("%x" % b["R"][0][3])
        b3 = byf.get(h + off + 3)
        hp1 = b3["R"][0][5] if b3 and 0 in b3["R"] else None
        res.append((h, V, "st%x" % r0[3], "hp%d" % r0[5], "hp'%s" % hp1, "".join(seq), "+53=%02x" % r0[53]))
    return res
if __name__ == "__main__":
    agg = collections.defaultdict(collections.Counter)
    for d in sorted(glob.glob("out/expB/*"), key=lambda s: (int(os.path.basename(s).split("_")[0]), s)):
        p = os.path.join(d, "enemylog.txt")
        if not os.path.exists(p): continue
        tag = os.path.basename(d)
        for r in analyse(p):
            if len(r) == 3: agg[tag]["gone"] += 1; continue
            _, V, st, hp, hp2, seq, f53 = r
            first = seq[0] if seq else "?"
            agg[tag][("pre" + st[2:], "->" + seq[:3], hp + ">" + hp2)] += 1
    for tag in agg:
        print(tag)
        for k, n in agg[tag].most_common(12): print("    ", n, k)
