"""recview.py <reclog.txt> [region index] : print the bytes of a logged record that change, with the frames."""
import sys
fn = sys.argv[1]; ri = int(sys.argv[2]) if len(sys.argv) > 2 else 0
rows = []
for ln in open(fn):
    p = ln.split()
    rows.append((int(p[0]), bytes.fromhex(p[1 + ri])))
n = len(rows[0][1])
prev = None
for f, r in rows:
    if prev is None or r != prev:
        ch = "" if prev is None else " ".join("%02x:%02x>%02x" % (i, prev[i], r[i]) for i in range(n) if prev[i] != r[i])
        print(f, ch if prev is not None else r.hex(" "))
    prev = r
