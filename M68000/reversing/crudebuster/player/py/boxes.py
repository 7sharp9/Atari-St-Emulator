"""boxes.py <reclog> lo hi : for each frame in [lo,hi] where the player's attack flag (+28) is set, print the attack box (+72..78) relative to the player position (+8 x word, +12 y word) and the body box (+64..70)."""
import sys, struct
fn, lo, hi = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
prev = None
for ln in open(fn):
    p = ln.split(); f = int(p[0])
    if f < lo or f > hi: continue
    r = bytes.fromhex(p[1])
    x = struct.unpack(">H", r[8:10])[0]; y = struct.unpack(">H", r[12:14])[0]
    ab = struct.unpack(">4h", r[72:80]); bb = struct.unpack(">4H", r[64:72])
    rel = lambda b: (((b[0] - x + 32768) & 0xffff) - 32768, ((b[1] - x + 32768) & 0xffff) - 32768, ((b[2] - y + 32768) & 0xffff) - 32768, ((b[3] - y + 32768) & 0xffff) - 32768)
    cur = (r[28], rel(ab), r[24], r[25], r[21], r[7], rel(bb))
    if cur != prev:
        print("%d flag=%d atk(rel x1,x2,y1,y2)=%s pose=%d var=%d fr=%d face=%d body=%s" % (f, r[28], cur[1], r[24], r[25], r[21], r[7], cur[6]))
    prev = cur
