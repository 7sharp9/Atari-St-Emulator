"""Dump records lo..hi of an events file: idx step pc target opcode kind."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from evt import read
ev = read(sys.argv[1]); lo = int(sys.argv[2]); hi = int(sys.argv[3])
flt = sys.argv[4] if len(sys.argv) > 4 else None
for i in range(lo, min(hi, len(ev))):
    st, pc, tg, op, k, f = ev[i]
    if flt:
        a, b = (int(x, 16) for x in flt.split('-'))
        if not (a <= (pc & 0xffffff) < b): continue
    print(f'{i:7d} {st:10d} pc=${pc:08x} tg=${tg:08x} op={op:04x} k={k} f={f}')
