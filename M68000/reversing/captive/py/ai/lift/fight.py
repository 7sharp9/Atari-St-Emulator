"""Attack the group in the cell ahead with the crew's hand icons: fight.py <snap> <out.snap> <rounds> [x:y ...]
Each round clicks every given icon point (default the eight hand icons) and prints the groups in the cells around
the party (position, flags +5, member hit points) and the party's position."""
import os, sys, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import probe_input as P
from probe_input import srv, w16, A6  # noqa

HANDS = ['204:135', '226:135', '250:135', '272:135', '204:155', '226:155', '250:155', '272:155']

def groups(s):
    """(index, address, x, y, flags, [member hp]) for every record of the group list 4532(A6)."""
    a = struct.unpack('>I', s.read(A6 + 4532, 4))[0] if False else 0x1c782
    out, i = [], 0
    while True:
        h = s.read(a, 8)
        size = struct.unpack('>h', h[2:4])[0]
        if size < 0:
            return out
        mem = s.read(a + 8, size - 8)
        out.append((i, a, h[0], h[1], h[5], [struct.unpack('>H', mem[k + 2:k + 4])[0] for k in range(0, size - 8, 8)]))
        a += size; i += 1

def near(s, r=3):
    px, py = w16(s, 26), w16(s, 28)
    return [(i, hex(a), x, y, f'{f:02x}', hp) for i, a, x, y, f, hp in groups(s) if abs(x - px) <= r and abs(y - py) <= r]

if __name__ == '__main__':
    s = srv(sys.argv[1]); pts = sys.argv[4:] or HANDS
    print('start', near(s))
    for rnd in range(int(sys.argv[3])):
        tot = dict.fromkeys(P.ADDRS, 0)
        for p in pts:
            P.drive(s, 'c' + p, tot)
        print('round', rnd, 'pos', w16(s, 26), w16(s, 28), 'face', w16(s, 30), near(s), flush=True)
    s('save', path=os.path.abspath(sys.argv[2])); s.close()
