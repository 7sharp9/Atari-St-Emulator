"""bottle_tp.py IN OUT ROOM X Y Z: INJECTED teleport (scratch verb 37 over object 562's event-5 block, queued as event 5), then dump the room's placement table."""
import sys, os
def root():
    d = os.path.abspath(os.path.dirname(__file__))
    while not os.path.exists(d + '/tools/rdis.py'): d = os.path.dirname(d)
    return os.environ.get('M68000_ROOT', d)
ROOT = root()
inp, out = os.path.abspath(sys.argv[1]), os.path.abspath(sys.argv[2]); room, x, y, z = map(int, sys.argv[3:7])
sys.path.insert(0, ROOT + '/reversing/cadaver/py/secrets/overlay/verbs2')
from h import H, set_body, inject5, A5
h = H(inp); r = h.r; h.owner = 562
print('start room', r.w(A5 + 1166))
set_body(h, [0x25, room, x, y, z, 0x17])
inject5(h, 562, 0, 5)
r.cmd('s 400000')
print('room now', r.w(A5 + 1166), 'hero bbox', list(r.mem(0x3833c - 0, 2)))
base = r.l(A5 + 56); n = r.w(A5 + 1152)
for i in range(n):
    e = r.mem(base + 70 * i, 70); rec = int.from_bytes(e[10:14], 'big')
    oid = r.w(rec + 4) if 0x1000 < rec < 0x7ffff else None
    print(i, 'obj', oid, 'bbox', list(e[0:6]), 'rec xyz', list(r.mem(rec, 3)) if oid is not None else None)
r.snap(out); h.close()
