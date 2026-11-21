"""Model + gate of the near-list builder $102dc (the second half of $101a8, run every frame while flying; it is the
selection that feeds $10344): clears 34/35 of every pool record, and pushes onto 144(A6) (array growing down from
3500(A6), count 572(A6)) each record with a type whose player-relative z (word, the world wraps at 65536) is within
-$2020..$2020, or, if z is further behind than that, whose x is within -$2020..$2020.
    python3 reversing/starglider/py/objects/nearlist.py [N] [--break]    -> 'nearlist a/b'"""
import sys, os, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import objlib as ol
from objlib import A6, Mem
from objpass import cmpw, M16, s16
BREAK = '--break' in sys.argv
POOL = A6 + 4762

def model(m):
    A3 = A6 + 3500; m.ww(A6 + 572, 0)
    n = m.rw(A6 + 472)
    if n:
        a4 = POOL
        for _ in range(n):
            m.wb(a4 + 35, 0); m.wb(a4 + 34, 0)
            if m.rw(a4) != 0:
                d1 = (m.rw(a4 + 4) - m.rw(A6 + 302)) & M16; d3 = (m.rw(a4 + 8) - m.rw(A6 + 306)) & M16
                push = False
                if not cmpw(d3, 0x2080 if BREAK else 0x2020).gt:
                    if cmpw(d3, 0xdfe1 if BREAK else 0xdfe0).gt: push = True
                    elif not cmpw(d1, 0x2020).gt and not cmpw(d1, 0xdfe0).lt: push = True
                if push: A3 -= 4; m.wl(A3, a4); m.ww(A6 + 572, m.rw(A6 + 572) + 1)
            a4 += 0x40
    m.wl(A6 + 144, A3)

def main():
    N = int(next((a for a in sys.argv[1:] if not a.startswith('--')), 40))
    rnd = random.Random(11)
    snap = ol.sg.SNAP_GAME1
    base = Mem(ol.sg.load_ram(snap))
    lines = []; cases = []
    for k in range(N):
        P = {}
        px = rnd.getrandbits(16); pz = rnd.getrandbits(16)
        for a, v in ((A6 + 302, px), (A6 + 306, pz), (A6 + 472, 107)): P[a] = v >> 8; P[a + 1] = v & 0xff
        for i in range(107):
            o = POOL + 0x40 * i
            for j in (34, 35): P[o + j] = rnd.choice([0, 0xff])
            if i >= 10:
                dx = rnd.choice([rnd.randint(-0x2100, 0x2100), rnd.randint(-0x8000, 0x7fff)]); dz = rnd.choice([rnd.randint(-0x2100, 0x2100), rnd.randint(-0x8000, 0x7fff)])
                for a, v in ((o + 4, px + dx), (o + 8, pz + dz)): P[a] = (v >> 8) & 0xff; P[a + 1] = v & 0xff
        cases.append(P); lines += ol.poke_lines(P) + ['callcap 102dc 400000 A6=%x' % A6]
    cc = ol.parse_callcaps(ol.repl_run(snap, lines))
    assert len(cc) == N
    cur = base.copy(); ok = 0; tot = 0
    for P, r in zip(cases, cc):
        for a, v in P.items(): cur.wb(a, v)
        live = cur.copy(); mod = cur.copy()
        for a, (o, n) in r['mem'].items(): live.wb(a, n)
        model(mod)
        rngs = [(A6 + 144, A6 + 148), (A6 + 572, A6 + 574), (A6 + 3500 - 4 * 110, A6 + 3500)] + [(POOL + 0x40 * i + 34, POOL + 0x40 * i + 36) for i in range(107)]
        bad = [a for lo, hi in rngs for a in range(lo, hi) if mod.rb(a) != live.rb(a)]
        ok += not bad; tot += mod.rw(A6 + 572)
        if bad and '--dbg' in sys.argv: print('BAD', [hex(a) for a in bad][:6])
    print('nearlist %d/%d' % (ok, N), 'records selected', tot)
main()
