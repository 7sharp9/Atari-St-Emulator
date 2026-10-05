"""Run-length statistics of one byte of a pool A type in an objlog.txt: actions.py objlog.txt <type hex> <byte offset> [variant filter]
prints: value, number of runs, total frames, min/max run length, and the transition matrix of run starts."""
import sys, collections
fn, t, off = sys.argv[1], int(sys.argv[2], 16), int(sys.argv[3])
vf = int(sys.argv[4], 16) if len(sys.argv) > 4 else None
runs = []; cur = None; lastf = None
for line in open(fn):
    if not line.startswith("A "): continue
    _, f, slot, hx = line.split(); f = int(f)
    b = bytes.fromhex(hx)
    if b[2] != t: continue
    if vf is not None and b[16] != vf: continue
    v = b[off]
    if cur and cur[0] == v and f == lastf + 1: cur[2] = f
    else:
        cur = [v, f, f]; runs.append(cur)
    lastf = f
st = collections.defaultdict(list)
for v, a, b in runs: st[v].append(b - a + 1)
print("value runs frames min max")
for v in sorted(st): print("%02x %d %d %d %d" % (v, len(st[v]), sum(st[v]), min(st[v]), max(st[v])))
tm = collections.Counter((runs[i][0], runs[i + 1][0]) for i in range(len(runs) - 1))
print("transitions:", " ".join("%02x>%02x:%d" % (a, b, n) for (a, b), n in sorted(tm.items())))
