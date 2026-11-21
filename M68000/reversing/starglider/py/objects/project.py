"""Model + gate of $10344 (called every frame from $fb74): the world-to-view pass over the near list.
For each record in the near list 144(A6) (572(A6) entries, built by $101a8 from the pool records within +-$2020 of the
player in x and z) with a non-zero type: rel = world - player (302/304/306(A6)), rotated by the 3x3 matrix at 360..376(A6)
($ec1e, Q14: muls, asl.l #2, swap), stored in 40/42/44(A4).  A record that is not exploding gets 35(A4) = $ff and goes on the
active list (152(A6), grows down from 4628(A6), count 576(A6)); one with z <= $2000, z > -$15842[type] and |x|,|y| <= 2z
(the view frustum) gets 34(A4) = $ff and goes on the view list (148(A6), grows down from 4064(A6), count 574(A6)).
    python3 reversing/starglider/py/objects/project.py [N] [--break]    -> 'project a/b'"""
import sys, os, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import objlib as ol
from objlib import A6, Mem
from objpass import cmpw, M16, s16
BREAK = '--break' in sys.argv
POOL = A6 + 4762

def rot(m, D1, D2, D3):
    def dot(a, b, c):
        t = 0
        for off, v in ((a, D1), (b, D2), (c, D3)):
            p = (m.rws(A6 + off) * s16(v)) << 2
            t += s16(((p & 0xffffffff) >> 16))
            t = s16(t)
        return t
    x = dot(360, 366, 372); y = dot(362, 368, 374); z = dot(364, 370, 376)
    m.ww(A6 + 398, x); m.ww(A6 + 400, y)
    return x, y, z

def model(m):
    A3 = m.rl(A6 + 144); n = m.rws(A6 + 572)
    if n == 0: return
    A5 = A6 + 4064; A2 = A6 + 4628
    m.ww(A6 + 574, 0); m.ww(A6 + 576, 0)
    for i in range(n):
        a4 = m.rl(A3 + 4 * i)
        t = m.rw(a4)
        if t == 0: continue
        D1 = m.rw(a4 + 4) - m.rw(A6 + 302); D2 = m.rw(a4 + 6) - m.rw(A6 + 304); D3 = m.rw(a4 + 8) - m.rw(A6 + 306)
        D1, D2, D3 = rot(m, D1, D2, D3)
        m.ww(a4 + 40, D1); m.ww(a4 + 42, D2); m.ww(a4 + 44, D3)
        if m.rb(a4 + 36) == 0:
            m.wb(a4 + 35, 0xff); A2 -= 4; m.wl(A2, a4); m.ww(A6 + 576, m.rw(A6 + 576) + 1)
        D3 &= M16
        if cmpw(D3, 0x2000).gt: continue
        m.ww(A6 + 592, t); m.ww(A6 + 594, D3)
        ext = (-s16(m.rw(0x15842 + 2 * t))) & M16
        if cmpw(D3, ext).le: continue
        d3 = (D3 * 2) & M16; d5 = (-s16(d3)) & M16
        if cmpw(D1 & M16, d5).lt: continue
        if cmpw(D1 & M16, d3).gt: continue
        if cmpw(D2 & M16, d5).lt: continue
        if cmpw(D2 & M16, d3).gt: continue
        m.wb(a4 + 34, 0xff); A5 -= 4; m.wl(A5, a4); m.ww(A6 + 574, m.rw(A6 + 574) + 1)
    m.wl(A6 + 148, A5); m.wl(A6 + 152, A2)

def tracked():
    return [(A6 + 148, A6 + 156), (A6 + 398, A6 + 402), (A6 + 572, A6 + 578), (A6 + 592, A6 + 596), (POOL, POOL + 20 * 0x40),
            (A6 + 4064 - 80, A6 + 4064), (A6 + 4628 - 80, A6 + 4628)]

def craft(rnd):
    P = {}
    def pw(a, v): P[a] = (v >> 8) & 0xff; P[a + 1] = v & 0xff
    n = rnd.randint(1, 12)
    pw(A6 + 572, n)
    for k, b in enumerate((0x5f800).to_bytes(4, 'big')): P[A6 + 144 + k] = b
    for off in range(360, 378, 2): pw(A6 + off, rnd.choice([0, 0x4000, 0xc000, rnd.getrandbits(16), rnd.randint(-0x4000, 0x4000) & 0xffff]))
    px = rnd.getrandbits(16); pz = rnd.getrandbits(16); py = rnd.getrandbits(16)
    pw(A6 + 302, px); pw(A6 + 304, py); pw(A6 + 306, pz)
    for i in range(n):
        o = POOL + 0x40 * i
        for k, b in enumerate(o.to_bytes(4, 'big')): P[0x5f800 + 4 * i + k] = b
        for j in range(0x40): P[o + j] = 0
        t = rnd.choice([0, 1, 2, 3, 4, 7, 9, 11, 13, 20, 24, 26, 27])
        pw(o, t); P[o + 36] = rnd.choice([0, 0, 0xff])
        pw(o + 4, px + rnd.randint(-3000, 3000)); pw(o + 6, py + rnd.randint(-1500, 1500)); pw(o + 8, pz + rnd.randint(-3000, 3000))
        P[o + 34] = rnd.choice([0, 0xff]); P[o + 35] = rnd.choice([0, 0xff])
    return P

def main():
    N = int(next((a for a in sys.argv[1:] if not a.startswith('--')), 150))
    rnd = random.Random(10)
    snap = ol.sg.SNAP_GAME1
    base = Mem(ol.sg.load_ram(snap))
    lines = []; cases = []
    for k in range(N):
        P = craft(rnd); cases.append(P)
        lines += ol.poke_lines(P) + ['callcap 10344 400000 A6=%x' % A6]
    cc = ol.parse_callcaps(ol.repl_run(snap, lines))
    assert len(cc) == N, (len(cc), N)
    cur = base.copy(); ok = 0; inview = 0; active = 0
    for P, r in zip(cases, cc):
        for a, v in P.items(): cur.wb(a, v)
        live = cur.copy(); mod = cur.copy()
        for a, (o, n) in r['mem'].items(): live.wb(a, n)
        if BREAK: cur.ww(A6 + 360, cur.rw(A6 + 360) + 1); mod = cur.copy()
        model(mod)
        bad = [a for lo, hi in tracked() for a in range(lo, hi) if mod.rb(a) != live.rb(a)]
        ok += not bad; inview += mod.rw(A6 + 574); active += mod.rw(A6 + 576)
        if bad and '--dbg' in sys.argv: print('BAD', [hex(a) for a in bad][:6], r['status'])
    print('project %d/%d' % (ok, N), 'records in view', inview, 'active', active)
main()
