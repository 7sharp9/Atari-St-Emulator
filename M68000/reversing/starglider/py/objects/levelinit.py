"""Model of the level initialiser $1523a (called once per life/level at $ca96) and its gate.
It clears the pool (4762(A6), $8c*64 bytes), builds the spare-record free list ($94c, 10 pointers to pool slots 0..9,
604(A6) = 10, 156(A6) = end of list), then places the level's records from slot 10 on: the list at the pointer
$22814[662(A6)] (words type, gx, gz, hit points; a zero type ends it; positions are grid * $290), with the per-type
start values below, and finally the two docking-bay records at $1218 / $1258 (positions from $f23e).
Usage (from M68000/):  python3 reversing/starglider/py/objects/levelinit.py [--break]
Expected: 'levelinit 5/5' (levels 1..5 on the g_game1 base) and, with --break, fewer."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import objlib as ol
from objlib import A6, Mem
import objpass
BREAK = '--break' in sys.argv
POOL = A6 + 4762

def model(m, d0=0):
    sim = objpass.Sim(m, d0)
    for i in range(0x8c * 64): m.wb(POOL + i, 0)
    for i in range(10): m.wl(0x94c + 4 * i, POOL + 0x40 * i)
    m.wl(A6 + 156, 0x94c + 40); m.ww(A6 + 604, 10)
    o = POOL + 0x280
    lst = m.rl(0x22814 + 4 * m.rws(A6 + 662)); D7 = 0
    def rnd():
        return sim.f23e()
    while True:
        t = m.rw(lst); lst += 2
        if t == 0: break
        sim.d0 = (sim.d0 & 0xffff0000)    # move.w (A1)+,D0 ; the later reads reload D0 = type below
        m.ww(o, t)
        gx = m.rw(lst); lst += 2; gz = m.rw(lst); lst += 2
        m.ww(o + 4, (gx * 0x290) & 0xffff); m.ww(o + 8, (gz * 0x290) & 0xffff)
        sim.d0 = (gz * 0x290) & 0xffffffff
        m.ww(o + 48, m.rw(lst)); lst += 2
        sim.d0 = (sim.d0 & 0xffff0000) | t
        if t == 7: m.ww(o + 6, 0xfe0c); m.ww(o + 16, 0xfa)
        elif t == 0x1b: m.ww(o + 6, 0xfd12); m.ww(o + 16, 0xfed4); m.ww(o + 48, 4); m.wb(o + 46, 0xff)
        elif t == 0x15: m.ww(o + 6, 0xff06); m.ww(o + 16, 0xff38)
        elif t == 0x14: m.ww(o + 6, 0xff6a)
        elif t == 1: m.ww(o + 16, 0x15 if BREAK else 0x14); m.wb(o + 46, 0xff)
        elif t == 0xf: m.ww(o + 16, 0x10); m.wb(o + 46, 0xff)
        elif t == 8: m.ww(o + 16, 0x19)
        elif t == 9: m.ww(o + 12, 0x400); m.ww(o + 16, 0x41 if BREAK else 0x40); m.ww(o + 22, 0x64)
        elif t == 2:
            m.ww(o + 6, 0xfed4); m.ww(o + 22, 0xfff1); r = rnd() & 0x7f; m.ww(o + 24, r); m.ww(o + 20, r)
        elif t == 0xe:
            m.ww(o + 6, 0xfe70); m.ww(o + 22, 0xffec); r = rnd() & 0x3f; m.ww(o + 20, r); m.ww(o + 24, r)
        elif t == 0xd: m.ww(o + 6, 0xf95c); m.ww(o + 16, 0xc8)
        elif t == 0x10: m.ww(o + 6, 0xff9c); m.ww(o + 16, 0xfed4)
        elif t in (5, 0x11): m.ww(o + 12, rnd() & 0xfff); m.wb(o + 2, 0xff)
        elif t == 3: m.ww(o + 12, rnd() & 0xfff)
        elif t == 4:
            m.wb(o + 2, 0xff); m.ww(o + 24, 1); m.wb(o + 66, 0xff); m.wb(o + 130, 0xff); m.wb(o + 194, 0xff)
            x = m.rw(o + 4); m.ww(o + 196, x); m.ww(o + 132, x + 0x100); m.ww(o + 68, x + 0x100 - 0x200)
            m.ww(o + 260, x + 0x5dc); m.ww(o + 324, x + 0x5dc - 0xbb8)
            z = m.rw(o + 8); m.ww(o + 200, z + 0x7d0); z2 = z + 0x7d0 * 2; m.ww(o + 136, z2); m.ww(o + 72, z2)
            m.ww(o + 264, z + 0x3e8); m.ww(o + 328, z + 0x3e8 - 0x7d0)
            m.ww(o + 64, 4); m.ww(o + 128, 4); m.ww(o + 192, 0xb); m.ww(o + 256, 9); m.ww(o + 320, 9)
            m.ww(o + 268, 0x400); m.ww(o + 272, 0x40); m.ww(o + 278, 0x64)
            m.ww(o + 332, 0xc00); m.ww(o + 336, 0x40); m.ww(o + 342, 0x64)
            d = 5 + m.rws(A6 + 662); m.ww(o + 304, d); m.ww(o + 368, d)
            D7 += 5; o += 0x140
        elif t == 6: m.wb(o + 2, 0xff); m.wb(o + 20, 0xff); m.ww(o + 22, 0x7d0)
        o += 0x40; D7 += 1
    D7 += 10; m.ww(A6 + 472, D7)
    sim.d0 = 0           # D0 = 0 from the terminating word, then each draw feeds the next
    for base, t in ((0x1218, 0x16), (0x1258, 0x18)):
        m.ww(base, t); m.wb(base + 2, 0xff)
        if base == 0x1218:
            m.ww(base + 4, rnd()); m.ww(base + 6, 0); m.ww(base + 8, rnd()); m.ww(base + 10, 0); m.ww(base + 12, rnd())
            m.ww(base + 14, 0); m.ww(base + 16, 0); m.ww(base + 28, 0); m.wb(base + 36, 0); m.wb(base + 20, 0)
        else:
            m.ww(base + 4, rnd()); m.ww(base + 6, 0); m.ww(base + 8, rnd()); m.ww(base + 10, 0); m.ww(base + 12, 0)
            m.ww(base + 14, 0x400); m.ww(base + 16, 0); m.ww(base + 28, 0); m.wb(base + 36, 0)

def tracked_ranges():
    return [(POOL, POOL + 0x8c * 64), (0x94c, 0x94c + 44), (A6 + 92, A6 + 108), (A6 + 156, A6 + 160), (A6 + 472, A6 + 474),
            (A6 + 538, A6 + 540), (A6 + 604, A6 + 606), (0x1218, 0x1218 + 0x80)]

def main():
    snap = ol.sg.SNAP_GAME1
    base = Mem(ol.sg.load_ram(snap))
    lines = []
    for lvl in range(1, 6):
        lines += ['ww %x %x' % (A6 + 662, lvl), 'callcap 1523a 3000000 A6=%x D0=0' % A6]
    cc = ol.parse_callcaps(ol.repl_run(snap, lines))
    ok = 0
    for lvl, r in zip(range(1, 6), cc):
        b = base.copy(); b.ww(A6 + 662, lvl)
        live = b.copy(); mod = b.copy()
        for a, (o, n) in r['mem'].items(): live.wb(a, n)
        model(mod)
        bad = [a for lo, hi in tracked_ranges() for a in range(lo, hi) if mod.rb(a) != live.rb(a)]
        un = [a for a in r['mem'] if not any(lo <= a < hi for lo, hi in tracked_ranges())]
        print(' level', lvl, 'live changed bytes', len(r['mem']), 'tracked mismatches', len(bad), 'untracked', [hex(a) for a in un][:4], 'records', mod.rw(A6 + 472))
        ok += not bad
    print('levelinit %d/5' % ok)
main()
