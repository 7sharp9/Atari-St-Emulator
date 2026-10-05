"""pos.py <reclog> lo hi [region]: per-frame x,y (32-bit 16.16 at +8,+12) deltas + action/state, compact."""
import sys, struct
fn, lo, hi = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]); ri = int(sys.argv[4]) if len(sys.argv) > 4 else 0
px = py_ = None
for ln in open(fn):
    p = ln.split(); f = int(p[0])
    if f < lo or f > hi: continue
    r = bytes.fromhex(p[1 + ri])
    x = struct.unpack(">I", r[8:12])[0]; y = struct.unpack(">I", r[12:16])[0]
    if px is not None:
        dx = ((x - px + 0x80000000) & 0xffffffff) - 0x80000000; dy = ((y - py_ + 0x80000000) & 0xffffffff) - 0x80000000
        print("%5d x=%08x y=%08x dx=%+.4f dy=%+.4f act=%02x sub=%02x f1=%02x held=%02x" % (f, x, y, dx / 65536, dy / 65536, r[4], r[5], r[1], r[16]))
    px, py_ = x, y
