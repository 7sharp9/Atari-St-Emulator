"""dumpram.py SNAP OUT [LO HI]: dump RAM (default 0..$100000) of a snapshot to a file via the REPL `m` command."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ssh import *
snap, out = sys.argv[1], sys.argv[2]
lo = int(sys.argv[3], 16) if len(sys.argv) > 3 else 0
hi = int(sys.argv[4], 16) if len(sys.argv) > 4 else 0x100000
r = R(snap)
buf = bytearray()
CH = 0x10000
a = lo
while a < hi:
    n = min(CH, hi - a)
    buf += r.mem(a, n)
    a += n
open(out, 'wb').write(buf)
r.close()
print('wrote', out, len(buf))
