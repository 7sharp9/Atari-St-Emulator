"""Read the game's cell list ($18f02..$18bde) from a snapshot taken at $19ce2: usage lists.py snap"""
import sys
from common import R
def cellof(a, base):
    dd = a - base; row = round(dd / 336); col = dd - row * 336
    assert col % 16 == 0, (hex(a), dd)
    return col // 16, row
def cell_list(snap):
    r = R(snap); base = r.l(0x12cfa) + 3360; end = r.l(0x18bde)
    L = []
    for p in range(0x18f02, end, 4):
        a = r.l(p); c = cellof(a, base); L.append((c[0], c[1]))
    return r.w(0x12c98), (r.w(0x12c68), r.w(0x12c6a)), L
if __name__ == '__main__':
    h, cam, L = cell_list(sys.argv[1]); print(h, cam, len(L)); print(L)
