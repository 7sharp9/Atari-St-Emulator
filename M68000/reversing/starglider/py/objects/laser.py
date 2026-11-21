"""Model + gate of the player's laser hit test, the part of $131f8 that runs when the shot counter 644(A6) reaches 0
($13294..$13386, entered here by callcap $131f8 with 644(A6) = 1 and 482(A6) odd, which takes the 'shot in flight' branch).
For every in-view record (list 148(A6), 574(A6) entries) that is alive and not type $b, the record's screen position
x = ((40(A4) << 530(A6)) / 44(A4)) + 508(A6), y likewise with 510(A6), and box half-widths ($15842/$1587e[type] scaled the
same way) are compared with the aim point 588/590(A6).  The first record whose box contains the aim point is hit:
indestructible (2(A4) < 0) or laser-immune (46(A4) != 0) records only play the sound; others lose a hit point (48(A4))
and when it goes negative explode (36 = $ff) and score $15a26[type] (BCD, via 212(A6)).  Type 4 (Energy Tower) toggles
the record 3 slots on (type $b <-> 0) when 24(A4) != 0 and the level is not 1.
    python3 reversing/starglider/py/objects/laser.py [N] [--break]    -> 'laser a/b'"""
import sys, os, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import objlib as ol
from objlib import A6, Mem
from objpass import cmpw, M16, s16, s32, divs
BREAK = '--break' in sys.argv
POOL = A6 + 4762

def scaled(m, val, D3, D5):
    """ext.l ; asl.l D5 ; divs D3 -> new D1 long (unchanged on overflow); returns low word"""
    D = s32(val) << (D5 & 63) if True else 0
    D &= 0xffffffff
    nd, ovf = divs(D, D3)
    return nd & M16, nd

def model(m):
    n = m.rws(A6 + 574)
    if n <= 0: return
    A5 = m.rl(A6 + 148)
    D5 = m.rw(A6 + 530) & 63
    m.ww(A6 + 644, m.rw(A6 + 644) - 1)       # subq.w #1,644(A6) (the caller entry value 1 -> 0)
    for i in range(n):
        a4 = m.rl(A5 + 4 * i)
        if m.rb(a4 + 36): continue
        t = m.rw(a4)
        if t == 0xb: continue
        D3 = m.rw(a4 + 44)
        if D3 == 0: continue
        D0 = t * 2
        d1, _ = scaled(m, s16(m.rw(a4 + 40)), D3, D5)
        d1 = (d1 + m.rw(A6 + 508)) & M16; m.ww(A6 + 596, d1)
        d4 = (m.rw(A6 + 588) - d1) & M16
        d6, _ = scaled(m, s16(m.rw(0x15842 + D0)), D3, D5); m.ww(A6 + 600, d6)
        if cmpw(d4, d6).pl: continue
        d4 = (-s16(d4)) & M16
        if cmpw(d4, d6).pl: continue
        d2, _ = scaled(m, s16(m.rw(a4 + 42)), D3, D5)
        d2 = (d2 + m.rw(A6 + 510)) & M16; m.ww(A6 + 598, d2)
        d4 = (m.rw(A6 + 590) - d2) & M16
        d6, _ = scaled(m, s16(m.rw(0x1587e + D0)), D3, D5); m.ww(A6 + 602, d6)
        if cmpw(d4, d6).pl: continue
        d4 = (-s16(d4)) & M16
        if cmpw(d4, d6).pl: continue
        if not (m.rb(a4 + 2) & 0x80) and m.rb(a4 + 46) == 0:
            m.wl(A6 + 184, m.rl(A6 + 184) + 1)
            m.ww(a4 + 48, m.rw(a4 + 48) - 1)
            if m.rw(a4 + 48) & 0x8000:
                m.wb(a4 + 36, 0xff); m.ww(a4 + 38, 0)
                m.ww(A6 + 212, m.rw(0x15a26 + D0 + (1 if BREAK else 0)))
                m.ww(A6 + 578, 0x222)
        if m.rw(a4) == 4:
            if m.rws(A6 + 662) != 1 and m.rw(a4 + 24) != 0:
                m.ww(a4 + 192, m.rw(a4 + 192) ^ 0xb)
        return
    return

def tracked():
    return [(A6 + 184, A6 + 188), (A6 + 212, A6 + 214), (A6 + 578, A6 + 580), (A6 + 596, A6 + 604), (A6 + 644, A6 + 646),
            (POOL, POOL + 14 * 0x40)]

def craft(rnd, base):
    P = {}
    def pw(a, v): P[a] = (v >> 8) & 0xff; P[a + 1] = v & 0xff
    def pb(a, v): P[a] = v & 0xff
    n = rnd.choice([1, 2, 3, 4, 5])
    for j in range(14 * 0x40): P[POOL + j] = 0
    pw(A6 + 574, n); pw(A6 + 644, 1); pw(A6 + 482, rnd.choice([1, 3, 5]))
    for k, b in enumerate((0x5f400).to_bytes(4, 'big')): P[A6 + 148 + k] = b
    pw(A6 + 530, rnd.choice([6, 7, 8])); pw(A6 + 508, rnd.choice([160, 150])); pw(A6 + 510, rnd.choice([70, 80]))
    pw(A6 + 588, rnd.randint(130, 190)); pw(A6 + 590, rnd.randint(50, 100)); pw(A6 + 662, rnd.choice([1, 2, 3]))
    pw(A6 + 212, 0); pw(A6 + 578, 0)
    for i in range(n):
        o = POOL + 0x40 * i
        for k, b in enumerate(o.to_bytes(4, 'big')): P[0x5f400 + 4 * i + k] = b
        t = rnd.choice([1, 3, 4, 7, 8, 9, 11, 13, 14, 15, 20, 21, 23, 24, 26, 27])
        pw(o, t); pb(o + 2, rnd.choice([0, 0, 0, 0xff])); pb(o + 36, rnd.choice([0, 0, 0, 0xff])); pb(o + 46, rnd.choice([0, 0, 0xff]))
        pw(o + 48, rnd.choice([0, 0, 1, 3])); pw(o + 24, rnd.choice([0, 1]))
        # aim the record at the crosshair roughly: x/y rel = (aim - centre) * z / 2^shift
        z = rnd.choice([300, 800, 1500, 4000, 9000]); pw(o + 44, z)
        sh = (P[A6 + 530 + 1])
        ax = ((P[A6 + 588] << 8 | P[A6 + 588 + 1]) - (P[A6 + 508] << 8 | P[A6 + 508 + 1])); ay = ((P[A6 + 590] << 8 | P[A6 + 590 + 1]) - (P[A6 + 510] << 8 | P[A6 + 510 + 1]))
        pw(o + 40, (ax * z >> sh) + rnd.randint(-60, 60)); pw(o + 42, (ay * z >> sh) + rnd.randint(-60, 60))
    return P

def main():
    N = int(next((a for a in sys.argv[1:] if not a.startswith('--')), 300))
    rnd = random.Random(9)
    snap = ol.sg.SNAP_GAME1
    base = Mem(ol.sg.load_ram(snap))
    lines = []; cases = []
    for k in range(N):
        P = craft(rnd, base); cases.append(P)
        lines += ol.poke_lines(P) + ['callcap 131f8 400000 A6=%x' % A6]
    cc = ol.parse_callcaps(ol.repl_run(snap, lines))
    assert len(cc) == N, (len(cc), N)
    cur = base.copy(); ok = 0; cov = {'hit': 0, 'kill': 0, 'none': 0}
    for P, r in zip(cases, cc):
        for a, v in P.items(): cur.wb(a, v)
        live = cur.copy(); mod = cur.copy()
        for a, (o, n) in r['mem'].items(): live.wb(a, n)
        b4 = bytes(mod.b); model(mod)
        bad = [a for lo, hi in tracked() for a in range(lo, hi) if mod.rb(a) != live.rb(a)]
        ok += not bad
        if bad and '--dbg' in sys.argv: print('BAD', [hex(a) for a in bad][:6], r['status'])
        cov['kill' if mod.rw(A6 + 212) else 'hit' if mod.rl(A6 + 184) != int.from_bytes(b4[A6 + 184:A6 + 188], 'big') else 'none'] += 1
    print('laser %d/%d' % (ok, N), 'outcomes', cov)
main()
