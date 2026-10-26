"""Midwinter terrain model (terrain.md): the generator $19962 (= $1999a + 4 x $199ec) and the grid
post-passes $1991a, $1d1d2, $197ec, transcribed on a copy of a snapshot's RAM so that the game's
out-of-grid reads (stale scratch rows) come out as the game's do.

usage:
  terrain_gen.py <entry.snap> <return.snap>          generator, snapshot at $19962 vs its return $19960
  terrain_gen.py targets <entry.snap> <x,y=out.snap>...   same, with the target $19cd4/$19cd6 poked to x,y
  terrain_gen.py post <post_in.snap> <post_out.snap>  post-passes, snapshot at $1991a vs $149ac
Each compares the 100 x 100 grid $404c4..$4a103 cell by cell. gate_terrain.py builds the snapshots.
"""
import os, struct, sys


def _root():
    d = os.path.dirname(os.path.abspath(__file__))
    while d != os.path.dirname(d):
        if os.path.exists(os.path.join(d, 'tools', 'rdis.py')):
            return d
        d = os.path.dirname(d)
    return os.environ['M68000_ROOT']


sys.path.insert(0, os.path.join(_root(), 'tools'))
from gfxview import load_ram  # noqa: E402

GRID, GRID_END = 0x404c4, 0x4a104
SCR66, WIN = 0x66000, 0x60000
P_SRC, P_DST, P_BUF_A, P_BUF_B, P_SHIFT = 0x2c352, 0x23060, 0x23064, 0x23068, 0x2305e
LVL, ORG_X, ORG_Y, TGT_X, TGT_Y, OFF_X, OFF_Y = 0x19cd8, 0x19cda, 0x19cdc, 0x19cd4, 0x19cd6, 0x19cde, 0x19ce0
A6 = 0x2c376


def s16(v):
    v &= 0xffff
    return v - 0x10000 if v & 0x8000 else v


class Mem:
    def __init__(self, ram):
        self.b = bytearray(ram)

    def l(self, a):
        return struct.unpack_from('>I', self.b, a)[0]

    def w(self, a):
        return struct.unpack_from('>H', self.b, a)[0]

    def setl(self, a, v):
        struct.pack_into('>I', self.b, a, v & 0xffffffff)

    def setw(self, a, v):
        struct.pack_into('>H', self.b, a, v & 0xffff)


def mid(m, a1, a2, a3, a4, shift):
    """$285a body: one new cell from four parents; a1's seed word enters the hash."""
    p1 = m.l(a1)
    s = (p1 + m.l(a2) + m.l(a3) + m.l(a4)) & 0xffffffff
    lo = ((s & 0xffff) ^ (p1 & 0xffff)) & 0x3fff
    avg = s16(s >> 16) >> 2
    d0 = s16((avg << 3) + 0x1388)
    d6 = s16(s16(s) >> (shift & 63))
    disp = s16(((d6 * d0) & 0xffffffff) >> 16)
    return ((avg + disp) & 0xffff) << 16 | lo


def run_285a(m, a1, a2, a3, a4, a5, n=49):
    shift = m.w(P_SHIFT)
    for i in range(n):
        m.setl(a5 + 4 * i, mid(m, a1 + 4 * i, a2 + 4 * i, a3 + 4 * i, a4 + 4 * i, shift))


def row_2ca6(m):
    """$2ca6: one source row (stride 200) -> two output rows of 100 cells."""
    src, bufa, bufb, dst = m.l(P_SRC), m.l(P_BUF_A), m.l(P_BUF_B), m.l(P_DST)
    run_285a(m, src, src + 4, src + 200, src + 204, bufa)                 # centres
    run_285a(m, bufa, bufb, src, src + 4, SCR66)                          # row edges
    run_285a(m, bufa, bufa + 4, src + 4, src + 204, SCR66 + 0x194)       # column edges
    for i in range(50):
        m.setl(dst, m.l(src + 4 * i)); dst += 4
        m.setl(dst, m.l(SCR66 + 4 * i)); dst += 4
    for i in range(50):
        m.setl(dst, m.l(SCR66 + 0x190 + 4 * i)); dst += 4
        m.setl(dst, m.l(bufa + 4 * i)); dst += 4
    m.setl(P_SRC, src + 200)
    m.setl(P_BUF_A, bufb)
    m.setl(P_BUF_B, bufa)
    m.setl(P_DST, dst)


def subdivide(m, src):
    """$1999a / $2c60: clear the edge scratch to -1, then 50 rows from src into the grid."""
    for a in range(SCR66, SCR66 + 202 * 8, 4):
        m.setl(a, 0xffffffff)
    m.setl(P_SRC, src)
    m.setl(P_DST, GRID)
    for _ in range(50):
        row_2ca6(m)


def window_2c20(m):
    """$2c20: copy the 50 x 50 window at (12(A6), 14(A6)) of the grid to $60000."""
    d0 = (m.w(A6 + 14) * 0x190) & 0xffffffff
    d1 = (((m.w(A6 + 12) * 4) & 0xffff) + d0) & 0xffff
    a0 = (GRID + s16(d1)) & 0xffffffff
    out = WIN
    for _ in range(50):
        for c in range(50):
            m.setl(out, m.l(a0 + 4 * c)); out += 4
        a0 += 0x190


def zoom_199ec(m):
    lvl = m.w(LVL)
    d0 = s16(s16(m.w(TGT_X) - m.w(ORG_X)) >> lvl) - 25
    d1 = s16(s16(m.w(TGT_Y) - m.w(ORG_Y)) >> lvl) - 25
    m.setw(OFF_X, d0)
    m.setw(OFF_Y, d1)
    m.setw(ORG_X, m.w(ORG_X) + (d0 << lvl))
    m.setw(ORG_Y, m.w(ORG_Y) + (d1 << lvl))
    m.setw(LVL, lvl - 1)
    m.setw(A6 + 12, m.w(OFF_X))                                          # $12964
    m.setw(A6 + 14, m.w(OFF_Y))
    window_2c20(m)
    subdivide(m, WIN)                                                    # $2c60
    m.setw(P_SHIFT, m.w(P_SHIFT) + 1)


def generate(m):
    """$19962."""
    m.setw(LVL, 4)
    m.setw(ORG_X, 0)
    m.setw(ORG_Y, 0)
    m.setw(P_SHIFT, 4)                                                   # $1999a
    subdivide(m, 0x4a104)
    for _ in range(4):
        zoom_199ec(m)


def heights_1991a(m):
    """$1991a: generator units -> render heights; the seed word is cleared."""
    for a in range(GRID, GRID_END, 4):
        h = s16(m.w(a))
        if h < 0:
            h = 0
        elif h <= 9:
            h = ((h + 1) * 0x18) & 0xffff
        else:
            h = h + 0xfa
        m.setl(a, (h & 0xffff) << 16)


def pads_1d1d2(m):
    """$1d1d2: each object in the table at $70010 (16-byte records, x.l, y.l) levels its cell's
    quad (-400, +4, -396) to the cell's own height."""
    n = s16(m.w(0x1d418))
    obj = 0x70010
    for _ in range(n + 1 if n >= 0 else 0):
        x = (m.l(obj) >> 2) & 0xffffffff
        x = (x & 0xffff0000) | ((x & 0xffff) >> 7)
        y = (m.l(obj + 4) >> 2) & 0xffffffff
        y = (y & 0xffff0000) | ((y & 0xffff) >> 7)
        row = (-(s16(y) - 0x63)) & 0xffff
        d0 = s16((x & 0xffff) + ((row * 0x64) & 0xffff))
        a0 = (m.l(0x12ce2) + 4 * d0) & 0xffffffff
        h = m.w(a0)
        for off in (-400, 4, -396):
            m.setw(a0 + off, h)
        obj += 16


def isqrt_198d8(d0):
    M = 0xffffffff
    d1, d2, d3, d4 = 0, d0 & M, 0, 0
    if d2 >= 4:
        while True:
            for _ in range(2):
                c = d2 & 1
                d2 >>= 1
                d3 = (d3 >> 1) | (c << 31)
            d4 = (d4 + 1) & 0xffff
            if d2 < 4:
                break
    first = True
    while True:
        if not first:
            for _ in range(2):
                x = d3 >> 31
                d3 = (d3 << 1) & M
                d2 = ((d2 << 1) | x) & M
        first = False
        d1 = (d1 << 1) & M
        if d1 < d2:
            d1 = (d1 + 2) & M
            d2 = (d2 - d1 + 1) & M
        d4 = (d4 - 1) & 0xffff
        if d4 == 0xffff:
            break
    return d1 >> 1


def shade_1988e(m, d1, d2, d3):
    if (d1 | d2 | d3) & 0xffff == 0:
        return 24
    d4 = s16(m.w(0x12c84))
    d2, d3 = s16(d2), s16(d3)
    d6 = s16(2 * d4 + 3 * d3)
    root = isqrt_198d8(d2 * d2 + d3 * d3 + d4 * d4)
    num = d6 << 3
    div = s16(root)
    q = int(num / div) if div else None                                 # divs truncates toward 0
    if q is None or not -0x8000 <= q <= 0x7fff:
        q = d6                                                           # overflow leaves D6
    q = s16(q)
    if q < 0:
        q = 0
    q += 2
    return 0x17 if q >= 0x18 else q


def shading_197ec(m):
    base, par = m.l(0x12ce2), m.w(0x157a8)
    h = lambda a: m.w(a)
    for i in range(10000):
        a = base + 4 * i
        row, col = divmod(i, 100)
        if (row + col + par) & 1:
            t = h(a - 400)
            m.b[a + 2] = shade_1988e(m, t, t - h(a - 396), t - h(a))
            t = h(a + 4)
            m.b[a + 3] = shade_1988e(m, t, -(t - h(a)), -(t - h(a - 396)))
        else:
            t = h(a - 396)
            m.b[a + 2] = shade_1988e(m, t, -(t - h(a - 400)), t - h(a + 4))
            t = h(a)
            m.b[a + 3] = shade_1988e(m, t, t - h(a + 4), -(t - h(a - 400)))


def compare(m, want):
    cells = [(a, m.b[a:a + 4] == want[a:a + 4]) for a in range(GRID, GRID_END, 4)]
    bad = [a for a, e in cells if not e]
    print(f'grid cells {len(cells) - len(bad)}/{len(cells)} match')
    for a in bad[:10]:
        i = (a - GRID) // 4
        print(f'  ${a:05x} row {i // 100} col {i % 100}: model {m.b[a:a+4].hex()} game {want[a:a+4].hex()}')
    return bad


def main_post():
    """post <post_in.snap> <post_out.snap>: $1991a, $1d1d2 (via $70010 as the game left it), $197ec."""
    m = Mem(load_ram(sys.argv[2])[0])
    want = load_ram(sys.argv[3])[0]
    heights_1991a(m)
    pads_1d1d2(m)
    shading_197ec(m)
    return 1 if compare(m, want) else 0


def main_targets():
    """targets <entry.snap> <x,y=out.snap>...: each out.snap is the game's return from $19962 after the
    host poked the target $19cd4/$19cd6 = x,y (decimal) into the entry state."""
    entry = load_ram(sys.argv[2])[0]
    grids, fails = [], 0
    for arg in sys.argv[3:]:
        xy, path = arg.split('=', 1)
        x, y = (int(v) for v in xy.split(','))
        m = Mem(entry)
        m.setw(TGT_X, x)
        m.setw(TGT_Y, y)
        generate(m)
        want = load_ram(path)[0]
        print(f'target {x},{y}: ', end='')
        fails += bool(compare(m, want))
        grids.append(want[GRID:GRID_END])
    same = sum(1 for i in range(len(grids)) for j in range(i) if grids[i] == grids[j])
    print(f'{len(grids)} targets, {fails} failing, {same} identical grid pairs')
    return 1 if fails or same else 0


def main():
    if sys.argv[1] == 'post':
        return main_post()
    if sys.argv[1] == 'targets':
        return main_targets()
    m = Mem(load_ram(sys.argv[1])[0])
    want = load_ram(sys.argv[2])[0]
    generate(m)
    cells = [(a, m.b[a:a + 4] == want[a:a + 4]) for a in range(GRID, GRID_END, 4)]
    ok = sum(1 for _, e in cells if e)
    print(f'grid cells {ok}/{len(cells)} match')
    bad = [a for a, e in cells if not e]
    for a in bad[:10]:
        i = (a - GRID) // 4
        print(f'  ${a:05x} row {i // 100} col {i % 100}: model {m.b[a:a+4].hex()} game {want[a:a+4].hex()}')
    for name, a in (('$19cd4 tgt', TGT_X), ('$19cda org', ORG_X), ('$19cde off', OFF_X), ('$2305e', P_SHIFT)):
        print(f'{name}: model {m.b[a:a+4].hex()} game {want[a:a+4].hex()}')
    return 0 if not bad else 1


if __name__ == '__main__':
    sys.exit(main())
