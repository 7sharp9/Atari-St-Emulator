"""Timeline of a level-5 objlog.txt (py/full.sh): for each pool A (slot,type) appearance: first frame, last frame, state sequence summary,
health at first sight; plus the frames where $80040/$80041/$80016 change (X columns of the F line, see full.sh) and the score ($8013c).
usage: milestones.py objlog.txt [types hex,...]"""
import sys
fn = sys.argv[1]
want = {int(t, 16) for t in sys.argv[2].split(",")} if len(sys.argv) > 2 else None
seg = {}   # (slot,type) -> list of [first,last,state seq]
last_seen = {}
for line in open(fn):
    if not line.startswith("A "): continue
    _, f, slot, hx = line.split(); f = int(f)
    b = bytes.fromhex(hx)
    t = b[2]
    if want and t not in want: continue
    k = (slot, t)
    if k in last_seen and f == last_seen[k][1] + 1 and last_seen[k][2] == b[16]:
        s = seg[k][-1]; s[1] = f
        if s[2][-1] != b[3]: s[2].append(b[3])
        s[3] = b[5]
    else:
        seg.setdefault(k, []).append([f, f, [b[3]], b[5], b[8] * 256 + b[9], b[12] * 256 + b[13]])
    last_seen[k] = (f, f, b[16])
rows = []
for (slot, t), L in seg.items():
    for s in L:
        rows.append((s[0], s[1], t, slot, s[3], s[4], s[5], s[2]))
for r in sorted(rows):
    print("f%d..f%d type%02x slot%s hp_last=%02x x=%04x y=%04x states=%s" % (r[0], r[1], r[2], r[3], r[4], r[5], r[6], " ".join("%02x" % s for s in r[7][:14]) + ("..." if len(r[7]) > 14 else "")))
