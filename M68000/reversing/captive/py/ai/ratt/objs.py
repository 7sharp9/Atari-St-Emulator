"""(promoted: reversing/captive/py/ai/ratt/objs.py) List the object list (13724(A6): records x,y,size then 4-byte items) of a snapshot, flag items of type $66.
Usage: objs.py <snap> [type_hex]"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from cap import R, W, StServer, snappath, A6  # noqa: E402  (cap finds the repo root: tools/rdis.py, or M68000_ROOT)
OUT = os.path.join(W, 'ratt')   # outputs (snapshots, renders) go here
os.makedirs(OUT, exist_ok=True)
def objlist(s):
    p = A6 + 2412   # the game's copy of the object list (= generator pointer 13724 = $1bf3a)
    a = p + 4; out = []
    while True:
        h = s.read(a, 4)
        sz = int.from_bytes(h[2:4], 'big')
        if sz & 0x8000 or sz == 0: break
        raw = s.read(a, sz)
        items = [raw[i:i + 4] for i in range(4, sz, 4)]
        out.append((a, raw[0], raw[1], items)); a += sz
    return p, out
if __name__ == '__main__':
    s = StServer(R); s('load', snapshot=snappath(sys.argv[1]))
    want = int(sys.argv[2], 16) if len(sys.argv) > 2 else None
    p, recs = objlist(s)
    print('list at', hex(p), 'records', len(recs), 'mode', int.from_bytes(s.read(A6 + 13564, 2), 'big'))
    for a, x, y, items in recs:
        for it in items:
            if want is None or it[0] == want or it[2] == want:
                print(f'${a:x} cell ({x},{y}) item', it.hex())
    s.close()
