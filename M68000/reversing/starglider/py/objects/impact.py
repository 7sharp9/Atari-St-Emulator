"""Gate: the collision consequence block of the outer loop ($cbb4..$cc42, inline in the frame loop, not a routine, so it is
driven from a natural stop: `bp cbb4`, poke the inputs, `bp ca9c`, read the results).  With 703(A6) set (a collision
found by $12fa2) and 172(A6) = the record: sound/flash 578 = $555; type 6 ends it; a record that is not indestructible
and is exploding (a ramming kill) scores $15a62[type] into 212(A6) (BCD, via $b91a) and, outside the missile view (712),
counts 196(A6); outside the missile view the ship takes a random heading kick (640 += (f23e & $3e) - $20, using $f23e)
and loses $159aa[level][type] shield; shield below zero sets 608 = 0 and 300 = 2 (destroyed).
    python3 reversing/starglider/py/objects/impact.py [N] [--break]     -> 'impact a/b'"""
import sys, os, random, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import objlib as ol
from objlib import A6, Mem
from objpass import Sim
BREAK = '--break' in sys.argv
POOL = A6 + 4762

def model(m):
    s = Sim(m)
    m.ww(A6 + 578, 0x555)
    a0 = m.rl(A6 + 172)
    if a0 == 0: return
    t = m.rw(a0)
    if t == 6: return
    d0 = t * 2
    if m.rb(a0 + 2) == 0 and m.rb(a0 + 36) != 0:
        m.ww(A6 + 212, m.rw(0x15a62 + d0 + (2 if BREAK else 0)))
        if m.rb(A6 + 712): return
        m.wl(A6 + 196, m.rl(A6 + 196) + 1)
    if m.rb(A6 + 712): return
    s.d0 = d0
    r = s.f23e() & 0x3e
    m.ww(A6 + 640, m.rw(A6 + 640) + r - 0x20)
    tab = m.rl(0x159aa + 4 * (m.rws(A6 + 662) & 0x3fff))
    dmg = m.rw(tab + d0)
    sh = m.rw(A6 + 608) - dmg
    if sh < 0:
        m.ww(A6 + 608, 0); m.ww(A6 + 300, 2)
    else: m.ww(A6 + 608, sh)

def main():
    N = int(next((a for a in sys.argv[1:] if not a.startswith('--')), 12))
    rnd = random.Random(5); snap = ol.sg.SNAP_GAME1; ok = 0; cov = set()
    base = Mem(ol.sg.load_ram(snap))
    for k in range(N):
        P = {}
        def pw(a, v): P[a] = (v >> 8) & 0xff; P[a + 1] = v & 0xff
        o = POOL + 0x40 * 30
        t = rnd.choice([1, 3, 7, 8, 9, 13, 15, 20, 24, 25, 27, 6, 4])
        for j in range(0x40): P[o + j] = 0
        pw(o, t); P[o + 2] = rnd.choice([0, 0, 0xff]); P[o + 36] = rnd.choice([0, 0xff, 0xff])
        lvl = rnd.choice([1, 2, 3, 4]); pw(A6 + 662, lvl)
        P[A6 + 703] = 0xff; pw(A6 + 658, 0); P[A6 + 717] = 0; P[A6 + 712] = rnd.choice([0, 0, 0xff]); pw(A6 + 542, 0)
        for j, b in enumerate(o.to_bytes(4, 'big')): P[A6 + 172 + j] = b
        pw(A6 + 608, rnd.choice([0x400, 0x2000, 0x8000, 0xffff])); pw(A6 + 212, 0); pw(A6 + 640, 0); pw(A6 + 300, 0)
        for j in range(6): P[A6 + 92 + j] = rnd.getrandbits(8)
        for j in range(4): P[A6 + 100 + j] = rnd.getrandbits(8)
        pw(0xc3ce, rnd.getrandbits(16))
        lines = ['bp cbb4 3000000'] + ol.poke_lines(P) + ['bp ca9c 400000', 'm %x 2' % (A6 + 608), 'm %x 2' % (A6 + 212), 'm %x 2' % (A6 + 640),
                 'm %x 4' % (A6 + 196), 'm %x 2' % (A6 + 300), 'm %x 6' % (A6 + 92), 'm %x 2' % (A6 + 578)]
        out = ol.repl_run(snap, lines)
        vals = re.findall(r'^((?:[0-9a-f]{2} )+[0-9a-f]{2})\s*$', out, re.M)
        if len(vals) < 7 or 'breakpoint $0000ca9c' not in out: print(' case', k, 'no stop / parse'); continue
        live = [bytes.fromhex(v.replace(' ', '')) for v in vals[-7:]]
        # the model starts from the polled snapshot state plus pokes; the snapshot's own values for fields not poked are irrelevant
        cur = base.copy()
        for a, v in P.items(): cur.wb(a, v)
        cur.wl(A6 + 196, base.rl(A6 + 196))
        # the stop at $cbb4 is the first natural pass; 196 and 578 start from the snapshot / that pass, so compare deltas
        l196 = int.from_bytes(live[3], 'big')
        model(cur)
        got = (int.from_bytes(live[0], 'big'), int.from_bytes(live[1], 'big'), int.from_bytes(live[2], 'big'), int.from_bytes(live[4], 'big'), int.from_bytes(live[6], 'big'))
        exp = (cur.rw(A6 + 608), cur.rw(A6 + 212), cur.rw(A6 + 640), cur.rw(A6 + 300), cur.rw(A6 + 578))
        # 212 is consumed (cleared) by the HUD $fc2a before the loop restarts only in $fb74; here it is read before that
        good = got == exp
        ok += good
        cov.add(('missile' if P[A6 + 712] else 'flight', 'kill' if (P[o + 2] == 0 and P[o + 36]) else 'bump', 'dead' if exp[3] == 2 else 'alive'))
        if not good: print(' case', k, 'type', t, 'lvl', lvl, 'live', got, 'model', exp, 'l196', l196, 'exp196', cur.rl(A6 + 196))
    print('impact %d/%d' % (ok, N), sorted(cov))
main()
