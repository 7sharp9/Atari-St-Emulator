"""Per-record timeline from an objlog.txt: prints (slot, type) segments: frames where (type, state+3, +16 variant, +18, +5 health, x, y) changes.
usage: states.py objlog.txt [f0 f1] [types hex list]"""
import sys, os
fn = sys.argv[1]
f0 = int(sys.argv[2]) if len(sys.argv) > 2 else 0
f1 = int(sys.argv[3]) if len(sys.argv) > 3 else 10**9
types = {int(t, 16) for t in sys.argv[4].split(",")} if len(sys.argv) > 4 else None
last = {}
for line in open(fn):
    if not line.startswith("A "): continue
    _, f, slot, hx = line.split()
    f = int(f)
    if f < f0 or f > f1: continue
    b = bytes.fromhex(hx)
    if types and b[2] not in types: continue
    key = (b[2], b[3], b[16], b[0] & 0xfd)
    k2 = (slot, b[2])
    cur = (b[3], b[16], b[5], b[0], b[1], b[53] if len(b) > 53 else 0)
    if last.get(k2) != ((b[3], b[16], b[18]) if os.environ.get("S18", "1") == "1" else (b[3], b[16])):
        print("f%d slot%s type%02x state%02x var%02x s18=%02x hp=%02x f0=%02x f1=%02x x=%04x y=%04x +30=%02x" % (f, slot, b[2], b[3], b[16], b[18], b[5], b[0], b[1], int.from_bytes(b[8:10], "big"), int.from_bytes(b[12:14], "big"), b[30]))
        last[k2] = (b[3], b[16], b[18]) if os.environ.get("S18", "1") == "1" else (b[3], b[16])
