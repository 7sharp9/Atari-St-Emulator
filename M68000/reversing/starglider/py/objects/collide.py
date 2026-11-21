"""Model + gate of the player/object collision routine $12fa2 (called once per frame from the outer loop).
It walks the active list 152(A6) (576(A6) records, those with 36 == 0) and tests the record's player-relative position
40/42/44 against the box |x|,|z| < $15842[type], |y| < $1587e[type] (z may be negative too).  The first record inside
the box decides: type $b (refuel hub) feeds 606(A6), type 6 (silo) docks the ship, types 1 and $f (walker, stomper)
and $1b (StarGlider One, only when 712 is set) hurt the ship / are not destroyed, anything else is destroyed (36 = $ff,
unless 2(A4) bit 7) and 703(A6) is set with 172(A6) = the record.
    python3 reversing/starglider/py/objects/collide.py [N] [--break]   -> 'collide a/b'"""
import sys, os, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import objlib as ol
from objlib import A6, Mem
from objpass import cmpw, M16, s16, Sim
BREAK = '--break' in sys.argv
POOL = A6 + 4762

def model(m):
    sim = Sim(m)
    def g(o): return m.rw(A6 + o)
    def clear():
        for o in (714, 703, 708, 707): m.wb(A6 + o, 0)
        m.wl(A6 + 172, 0)
    if m.rb(A6 + 714): return
    n = g(576); A3 = m.rl(A6 + 152)
    if n == 0: return clear()
    for i in range(n):
        a4 = m.rl(A3 + 4 * i)
        if m.rb(a4 + 36): continue
        t = m.rw(a4); D1 = m.rw(a4 + 40); D2 = m.rw(a4 + 42); D3 = m.rw(a4 + 44)
        ex = m.rw(0x15842 + 2 * t); ey = m.rw(0x1587e + 2 * t)
        if not cmpw(D3, ex).mi: continue
        D3 = (-s16(D3)) & M16
        if cmpw(D3, ex).pl: continue
        if cmpw(D1, ex).pl: continue
        D1 = (-s16(D1)) & M16
        if cmpw(D1, ex).pl: continue
        if cmpw(D2, ey).pl: continue
        D2 = (-s16(D2)) & M16
        if cmpw(D2, ey).pl: continue
        if m.rb(A6 + 713):
            if t == 0xb: return clear()
            m.ww(A6 + 630, 0x10); m.ww(A6 + 636, 0)
        else:
            if t == 0xb: return refuel(m, a4)
            if t == 6: return silo(m, a4, clear)
        def hit():
            if not (m.rb(a4 + 2) & 0x80):
                m.wb(a4 + 36, 0xff); m.ww(a4 + 38, 0)
            m.wb(A6 + 703, 0xff); m.wl(A6 + 172, a4)
        def flag():
            m.wb(A6 + 703, 0xff); m.wl(A6 + 172, a4)
        if t == 0x1b:
            if m.rb(A6 + 712) == 0: return flag()
            m.ww(a4 + 48, m.rw(a4 + 48) - 1)
            if not (m.rw(a4 + 48) & 0x8000): return flag()
            return hit()
        if t in (1, 0xf):
            if m.rb(A6 + 712): return hit()
            d = m.rw(A6 + 608) - 0x1f40
            m.ww(A6 + 608, d if d >= 0 else 0)
            return flag()
        return hit()
    clear()

def refuel(m, a4):
    if m.rb(A6 + 708) == 0 and m.rb(A6 + 712) == 0:
        m.wb(A6 + 708, 0xff)
        ok = (not cmpw(m.rw(a4 + 44), 0x7d0).pl) and (not cmpw(m.rw(a4 + 44), 0x79e).mi)
        if ok:
            d0 = (m.rw(a4 + 12) + m.rw(A6 + 316)) & 0xfff
            ok = (not cmpw(d0, 0x9f4).pl) and (not cmpw(d0, 0x60c).mi) and (not cmpw(m.rw(a4 + 40), 0x2bc).pl) and (not cmpw(m.rw(a4 + 40), 0xfd44).mi)
        m.wb(A6 + 707, 0xff if ok else 0)
    if m.rb(A6 + 707):
        m.ww(A6 + 578, 0x500)
        d = m.rw(A6 + 606) + 0x190
        m.ww(A6 + 606, 0xffff if d > 0xffff else d)

def silo(m, a4, clear):
    d0 = (m.rw(a4 + 12) + m.rw(A6 + 316)) & 0xfff
    if cmpw(d0, 0xead if BREAK else 0xeac).pl or not cmpw(d0, 0x154).pl:
        pass
    else:
        m.wb(A6 + 703, 0xff); m.wl(A6 + 172, a4); return
    m.wl(A6 + 192, m.rl(A6 + 192) + 1)
    m.ww(A6 + 608, 0xffff); m.wb(A6 + 714, 0xff)
    for b in (0x1218, 0x1258):
        m.ww(b + 4, m.rw(a4 + 4)); m.ww(b + 6, m.rw(a4 + 6)); m.ww(b + 8, m.rw(a4 + 8))
    m.ww(0x1218 + 6, m.rw(0x1218 + 6) - 0xb4)
    m.ww(0x1258 + 10, 0x400); m.ww(0x1258 + 12, 0x400); m.ww(0x1258 + 8, m.rw(0x1258 + 8) - 0x15e)
    m.ww(A6 + 302, m.rw(a4 + 4)); m.ww(A6 + 304, m.rw(a4 + 6) - 0xb4); m.ww(A6 + 306, m.rw(a4 + 8) - 0x320)
    m.ww(0x1218 + 12, 0); m.ww(A6 + 314, 0); m.ww(A6 + 316, 0); m.ww(A6 + 318, 0)
    m.ww(0xc3d4, 0xfff0); m.wl(A6 + 168, a4)
    for o in (703, 708, 707): m.wb(A6 + o, 0)          # $12fec: the tail of the clear without 714
    m.wl(A6 + 172, 0)

def tracked():
    return [(A6 + 172, A6 + 176), (A6 + 192, A6 + 196), (A6 + 302, A6 + 308), (A6 + 314, A6 + 320), (A6 + 578, A6 + 580),
            (A6 + 606, A6 + 610), (A6 + 630, A6 + 638), (A6 + 703, A6 + 704), (A6 + 707, A6 + 709), (A6 + 714, A6 + 715),
            (A6 + 168, A6 + 172), (POOL, POOL + 8 * 0x40), (0x1218, 0x1218 + 0x80), (0xc3d4, 0xc3d6)]

def craft(rnd, base):
    P = {}
    def pw(a, v): P[a] = (v >> 8) & 0xff; P[a + 1] = v & 0xff
    def pb(a, v): P[a] = v & 0xff
    n = rnd.choice([0, 1, 2, 3])
    pw(A6 + 576, n); 
    for k, b in enumerate((0x5f000).to_bytes(4, 'big')): P[A6 + 152 + k] = b     # list array in free RAM we poke
    for i in range(n):
        o = POOL + 0x40 * i
        for k, b in enumerate(o.to_bytes(4, 'big')): P[0x5f000 + 4 * i + k] = b
        t = rnd.choice([1, 2, 3, 6, 7, 8, 9, 11, 11, 13, 15, 27, 27, 24, 26, 14, 4])
        for j in range(0x40): P[o + j] = 0
        pw(o, t); pb(o + 2, rnd.choice([0, 0, 0xff]))
        ex = 0; 
        pw(o + 12, rnd.getrandbits(12)); pw(o + 48, rnd.randint(0, 3)); pb(o + 36, rnd.choice([0, 0, 0, 0xff]))
        pw(o + 4, rnd.getrandbits(16)); pw(o + 6, rnd.getrandbits(16)); pw(o + 8, rnd.getrandbits(16))
        ex = base.rw(0x15842 + 2 * t); ey = base.rw(0x1587e + 2 * t)
        if rnd.random() < 0.7 and ex:        # inside (or just outside) the type's box
            e = rnd.choice([ex, ex, ex + 2, ex - 2]); f = rnd.choice([ey, ey, ey + 2, ey - 2])
            pw(o + 40, rnd.randint(-e, e)); pw(o + 42, rnd.randint(-f, f)); pw(o + 44, rnd.randint(-e, e))
            if t == 11 and rnd.random() < 0.7: pw(o + 44, rnd.randint(0x790, 0x7d8)); pw(o + 40, rnd.randint(-0x2c0, 0x2c0))
        else:
            pw(o + 40, rnd.choice([0, 3, 0xfffd, 0x100, 0xff00, 0x2b0, 0xfd50, rnd.getrandbits(16)]))
            pw(o + 42, rnd.choice([0, 7, 0xfff0, 0x40, rnd.getrandbits(16)]))
            pw(o + 44, rnd.choice([0, 0x7a0, 0x7d1, 0x79d, 0xfe00, 0x20, 0xffe0, 0xf000, 0x300, rnd.getrandbits(16)]))
    pb(A6 + 713, rnd.choice([0, 0, 0, 0xff])); pb(A6 + 714, rnd.choice([0, 0, 0, 0, 0xff])); pb(A6 + 712, rnd.choice([0, 0, 0xff]))
    pb(A6 + 703, rnd.choice([0, 0xff])); pb(A6 + 707, rnd.choice([0, 0xff])); pb(A6 + 708, rnd.choice([0, 0xff]))
    pw(A6 + 608, rnd.choice([0x100, 0x1f40, 0x1f41, 0x8000, 0xffff])); pw(A6 + 606, rnd.choice([0, 0x1000, 0xfe80, 0xffff]))
    pw(A6 + 316, rnd.choice([0, 0x7ff, 0x9f0, 0x600, rnd.getrandbits(12)]))
    if n and rnd.random() < 0.3:                  # steer the first record to the silo / refuel boxes
        o = POOL; t = rnd.choice([6, 6, 11]); pw(o, t)
        ex = base.rw(0x15842 + 2 * t); ey = base.rw(0x1587e + 2 * t)
        pw(o + 40, rnd.randint(-ex + 1, ex - 1)); pw(o + 42, rnd.randint(-ey + 1, ey - 1)); pw(o + 44, rnd.randint(-ex + 1, ex - 1))
        if t == 11: pw(o + 44, rnd.randint(0x790, 0x7d8)); pw(o + 40, rnd.randint(-0x2c0, 0x2c0))
        pw(A6 + 316, 0); pb(o + 36, 0); P[A6 + 713] = 0; P[A6 + 714] = 0; P[A6 + 712] = rnd.choice([0, 0, 0xff])
        pw(o + 12, rnd.choice([0xeab, 0xeac, 0xead, 0x153, 0x154, rnd.getrandbits(12)]))
        pw(o + 12, (rnd.choice([0xeab, 0xeac, 0xead, 0x153, 0x154, 0x9f3, 0x9f4, 0x60b, 0x60c, rnd.getrandbits(12)])) & 0xfff)
    return P

def main():
    N = int(next((a for a in sys.argv[1:] if not a.startswith('--')), 200))
    rnd = random.Random(12)
    snap = ol.sg.SNAP_GAME1
    base = Mem(ol.sg.load_ram(snap))
    lines = []; cases = []
    for k in range(N):
        P = craft(rnd, base); cases.append(P)
        lines += ol.poke_lines(P) + ['callcap 12fa2 400000 A6=%x' % A6]
    cc = ol.parse_callcaps(ol.repl_run(snap, lines))
    assert len(cc) == N, (len(cc), N)
    cur = base.copy(); ok = 0; cov = {}
    for P, r in zip(cases, cc):
        for a, v in P.items(): cur.wb(a, v)
        live = cur.copy(); mod = cur.copy()
        for a, (o, n) in r['mem'].items(): live.wb(a, n)
        before = bytes(mod.b); before_606 = mod.rw(A6 + 606)
        model(mod)
        bad = [a for lo, hi in tracked() for a in range(lo, hi) if mod.rb(a) != live.rb(a)]
        ok += not bad
        k = ('refuel' if mod.rw(A6 + 606) != before_606 else '') + ('dock' if mod.rb(A6 + 714) and not before[A6 + 714] else 'flag' if mod.rb(A6 + 703) else 'none') + ('/kill' if any(mod.rb(POOL + 0x40 * i + 36) and not before[POOL + 0x40 * i + 36] for i in range(3)) else '')
        cov[k] = cov.get(k, 0) + 1
        if bad and '--dbg' in sys.argv: print('BAD', [hex(a) for a in bad][:6])
    print('collide %d/%d' % (ok, N), 'outcomes', cov)
main()
