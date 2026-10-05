"""seq.py <reclog.txt> <lo> <hi> field,field,... : per-frame table of selected byte offsets (hex) of region 0 between frames lo..hi, printing only frames where any listed field changed."""
import sys
fn, lo, hi = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]); fl = [int(x, 16) for x in sys.argv[4].split(",")]
ri = int(sys.argv[5]) if len(sys.argv) > 5 else 0
prev = None
print("frame " + " ".join("%02x" % x for x in fl))
for ln in open(fn):
    p = ln.split(); f = int(p[0])
    if f < lo or f > hi: continue
    r = bytes.fromhex(p[1 + ri]); cur = tuple(r[x] for x in fl)
    if cur != prev: print("%5d " % f + " ".join("%02x" % v for v in cur))
    prev = cur
