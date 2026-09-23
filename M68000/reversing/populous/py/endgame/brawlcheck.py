"""brawlcheck.py <capture.bin> - the Armageddon brawl against a capframes.py capture ($db4c entry/exit).

Checked on every captured frame whose entry state has Armageddon on ($3d524 != 0):
  - magnets: both side states +2, $3c4ca and $3d526 are $820 (32,32) after the frame (`$dec4`);
  - vacate: every settlement (flags 1, str > 0) at entry leaves as a walker: flags (f & ~1) | 2,
    +12 = +10 = 0 (`$e270`), and no entity is a settlement after the frame;
  - release: its footprint is released by `$10366(e, 1)` - the whole $36e78 map and $3c522 overlay
    after the frame equal the entry state with every vacated settlement released in entity order;
  - pop: side state +8 after the frame is the sum of the entry strengths of live entities
    (only on frames without a fight or new entity, where the loop totals cannot change mid-frame).
The combat rounds are fightcheck.py's; walker steering under Armageddon is $f6b2 (ai/livecheck dir).
"""
import os, struct, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from capframes import RECLEN
from people_model import Mem, ENT, ESZ, SIDE, MAP, OBJ, DOFF, check, ent

ARMA, MAG = 0x3d524, 0x820


def release(m, e):
    """$10366(e, 1) on Mem m."""
    c0, own = e['cell'], (0x1f + e['side']) & 0xff
    castle = m.b(OBJ + c0) == 0x2a
    n = 25 if castle else 17
    for k in range(n):
        off = FOOT[k]
        if check(m, c0, off) == 1: continue
        c = c0 + off
        if castle or k < 9: m.setb(OBJ + c, 0)
        if m.b(MAP + c) == own: m.setb(MAP + c, 0x0f)
    if not castle: m.setb(OBJ + c0, 0)


# $22b4e: the 25 footprint offsets (read from ai/M0.snap; the first 17 are people_model.DOFF)
FOOT = DOFF + [-127, -62, 66, 129, 127, 62, -66, -129]


def main(path):
    data = open(path, 'rb').read()
    nrec = len(data) // RECLEN
    stats = {}
    def tally(k, ok, why=None):
        a = stats.setdefault(k, [0, 0, []]); a[0] += bool(ok); a[1] += 1
        if not ok and len(a[2]) < 5: a[2].append(why)
    last = seen = None
    for f in range(nrec // 2):
        P = Mem(data[2 * f * RECLEN:(2 * f + 1) * RECLEN]); Q = Mem(data[(2 * f + 1) * RECLEN:(2 * f + 2) * RECLEN])
        if P.w(ARMA) == 0: continue
        frame = P.uw(0x3c4c8)
        if frame == seen: continue                       # capframes re-dumps after the game has ended
        seen = frame
        n, qn = P.w(0x3c4e2), Q.w(0x3c4e2)
        E = [ent(P, i) for i in range(n)]; QE = [ent(Q, i) for i in range(qn)]
        mags = [Q.w(SIDE + 16 * s + 2) for s in (0, 1)] + [Q.w(0x3c4ca), Q.w(0x3d526)]
        tally('magnets', all(v == MAG for v in mags), (frame, mags))
        M = Mem(data[2 * f * RECLEN:(2 * f + 1) * RECLEN])
        nv = 0
        for i, e in enumerate(E):
            if e['str'] <= 0 or e['fl'] & 1 == 0: continue
            q = QE[i]; nv += 1
            tally('vacate', q['fl'] == (e['fl'] & ~1 | 2) and q['anim'] == 0 and q['off'] == 0,
                  (frame, i, e['fl'], q['fl'], q['anim'], q['off']))
            release(M, e)
        tally('no_settlement_after', not any(q['str'] > 0 and q['fl'] & 1 for q in QE), frame)
        mp = M.m[0x36e78]; qp = Q.m[0x36e78]
        dmap = [a for a in range(0x1000) if mp[MAP - 0x36e78 + a] != qp[MAP - 0x36e78 + a]]
        dobj = [a for a in range(0x1000) if mp[OBJ - 0x36e78 + a] != qp[OBJ - 0x36e78 + a]]
        tally('release_map+overlay', not dmap and not dobj,
              (frame, nv, ['%x:%02x>%02x' % (a, mp[MAP - 0x36e78 + a], qp[MAP - 0x36e78 + a]) for a in dmap[:6]],
               ['%x:%02x>%02x' % (a, mp[OBJ - 0x36e78 + a], qp[OBJ - 0x36e78 + a]) for a in dobj[:6]]))
        if nv: stats.setdefault('frames_with_vacates', [0, 0, []])[0] += 1
        fights = sum(1 for q in QE if q['str'] > 0 and q['fl'] & 8) or sum(1 for e in E if e['str'] > 0 and e['fl'] & 8)
        if not fights and qn == n:
            pop = [0, 0]
            for e in E:                                  # accumulated in the loop from entry strengths
                if e['str'] > 0: pop[e['side']] += e['str']
            qp = [Q.l(SIDE + 16 * s + 8) for s in (0, 1)]
            tally('pop', pop == qp, (frame, pop, qp))
        last = (frame, [Q.l(SIDE + 16 * s + 8) for s in (0, 1)], sum(q['str'] > 0 for q in QE))
    for k, (a, b, w) in stats.items():
        print('%-22s %d/%d' % (k, a, b) if b else '%-22s %d' % (k, a))
        for x in w: print('   BAD', x)
    print('last frame', last)


if __name__ == '__main__':
    main(sys.argv[1])
