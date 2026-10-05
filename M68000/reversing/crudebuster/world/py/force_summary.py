"""force_summary.py <force log>: per case: alive at end, died frame, children spawned (baseline-subtracted), P changes."""
import sys, re
log = sys.argv[1]
cases = []; cur = None
for l in open(log):
    l = l.rstrip("\n")
    if l.startswith("CASE"):
        cur = {"hdr": l, "R": [], "N": [], "D": None, "P": []}
        m = re.match(r"CASE (\w) (\d+) (\w+) var=(\d+)", l)
        cur["pool"], cur["type"], cur["mode"], cur["var"] = m.group(1), int(m.group(2)), m.group(3), int(m.group(4))
        cases.append(cur)
    elif cur is not None:
        t = l.split(" ", 2)
        if t[0] == "R": cur["R"].append((int(t[1]), t[2]))
        elif t[0] == "N":
            n, rest = int(t[1]), t[2].split(" ")
            cur["N"].append((n, rest[0], int(rest[1]), rest[2]))
        elif t[0] == "D": cur["D"] = int(t[1])
        elif t[0] == "P": cur["P"].append(l)
base = {}
for c in cases:
    if c["type"] == 255:
        base[c["mode"]] = set((n, p, h[4:6], h[2:4]) for n, p, s, h in c["N"])
def tytxt(pool, hexrec): return int(hexrec[4:6], 16)
for c in cases:
    if c["type"] == 255: continue
    b = base.get(c["mode"], set())
    kids = {}
    for n, p, s, h in c["N"]:
        key = (n, p, h[4:6], h[2:4])
        if key in b: continue
        ty = int(h[4:6], 16); var = int(h[32:34], 16) if p != "C" else 0
        kids.setdefault((p, ty, var), []).append(n)
    ptxt = ""
    if c["P"]:
        first = c["P"][0].split(" ", 2)[2]
        chg = [x.split(" ", 2)[2] for x in c["P"]]
        ptxt = "P:" + " > ".join(sorted(set(chg), key=chg.index))
    last = c["R"][-1][1][:36] if c["R"] else "?"
    print("%s%-3d v%-2d %-4s died=%-4s kids=%s %s" % (c["pool"], c["type"], c["var"], c["mode"], c["D"], " ".join("%s%d.%d@%s" % (p, t, v, ",".join(map(str, ns[:3]))) for (p, t, v), ns in sorted(kids.items())), ptxt))
