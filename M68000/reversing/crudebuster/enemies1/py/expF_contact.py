"""Contact damage check on the expA logs: frames where P1 loses exactly 1 hp while slot 0 has +6 bit 4 ($90, written by $f700) -> does the enemy lose 1 hp within 3 frames and does P1's score rise by the 'hurt' points?"""
import sys, os, glob, collections
sys.path.insert(0, os.path.dirname(__file__))
from loglib import frames
res = collections.Counter(); per = collections.defaultdict(collections.Counter)
for d in glob.glob("out/expA/*"):
    p = os.path.join(d, "enemylog.txt")
    if not os.path.exists(p): continue
    fr = list(frames(p)); t = int(os.path.basename(d).split("_")[0])
    for i in range(1, len(fr) - 3):
        a, b = fr[i-1], fr[i]
        if a["P"] is None or b["P"] is None: continue
        if a["P"][0x13] - b["P"][0x13] == 1 and 0 in b["R"] and b["R"][0][6] & 0x10:
            r0 = a["R"].get(0)
            if r0 is None: continue
            hp_after = min(f["R"][0][5] if 0 in f["R"] else 0 for f in fr[i:i+4])
            ok = hp_after < r0[5] or any(0 not in f["R"] for f in fr[i:i+4])
            res[ok] += 1; per[t][ok] += 1
print("contact events (P1 -1 hp with enemy +6 bit 4):", dict(res))
for t in sorted(per): print("  type", t, dict(per[t]))
