"""walker_diff.py - differential test: walker_ref.py ($f2f4 scan, $f6b2 magnet/leader/knight) vs the
real 68000 routines via callcap.

Pattern of reversing/populous/py/ai_diff.py: per base snapshot, generate N randomized states per
routine (entity array, 15x15 terrain/overlay/occupancy/visit neighbourhood, side modes, leaders,
magnets, knight targets, armageddon, options, controller flags, RNG seed), write them with `w`,
poke the stack arguments (entity pointer long, index word) at the entry SP, run `callcap`, and
compare the full non-stack memory delta plus the returned D0.w with the model.

usage: python walker_diff.py [N_per_routine_per_snap] [seed]
"""
import os, random, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import walker_ref as W                                    # also puts reversing/populous/py on sys.path
from ai_diff import repl, get_a7, Poker, S, SNAPS
from ai_ref import rw, sidest, rec
import hx

NENT = 24
TERRS = [0, 0x0f, 0x0f, 0x0f, 0x0f, 0x1f, 0x20, 0x2f, 0x30, 0x35, 0x42, 0x10]
OVLS = [0] * 12 + [0x20, 0x21, 0x25, 0x29, 0x2a, 0x2c, 0x2d, 0x36, 0x80, 0xa9]
EFLAGS = [1, 2, 2, 2, 8, 9, 0x12, 0x22, 0x42, 0x80, 4, 0, 0x0a]


def rand_cell(rnd):
    x = rnd.choice([0, 1, 62, 63] + [rnd.randint(0, 63)] * 6)
    y = rnd.choice([0, 1, 62, 63] + [rnd.randint(0, 63)] * 6)
    return y * 64 + x


def near(rnd, cell, r):
    x = min(63, max(0, (cell & 63) + rnd.randint(-r, r)))
    y = min(63, max(0, (cell >> 6) + rnd.randint(-r, r)))
    return y * 64 + x


def rand_entities(P, rnd, centre, walker_i):
    P.w(W.COUNT, NENT)
    for i in range(NENT):
        p = W.ENT + i * W.ESZ
        P.b(p, rnd.choice(EFLAGS))
        P.b(p + 1, rnd.randint(0, 1))
        P.b(p + 2, rnd.randint(0, 4))
        P.w(p + 4, rnd.choice([rnd.randint(1, 3000), 0, -3 & 0xffff, rnd.randint(1, 60)]))
        P.w(p + 8, near(rnd, centre, 6) if rnd.random() < 0.6 else rnd.randint(0, 0xfff))
        P.w(p + 10, W.ring(P.m, rnd.randint(0, 8)))
        P.w(p + 12, rnd.randint(0, 7))
        P.l(p + 14, 0)
        P.b(p + 20, 0)
        P.b(p + 21, rnd.randint(0, 255))


def rand_hood(P, rnd, cell, rad):
    x0, y0 = cell & 63, cell >> 6
    style = rnd.random()
    for y in range(y0 - rad, y0 + rad + 1):
        for x in range(x0 - rad, x0 + rad + 1):
            if not (0 <= x < 64 and 0 <= y < 64): continue
            c = y * 64 + x
            if style < 0.25:
                t = rnd.choice([0x0f] * 8 + TERRS)
            elif style < 0.6:
                t = rnd.choice(TERRS)
            elif style < 0.8:                              # no unclaimed flat land: categories 1-4
                t = rnd.choice([0x1f, 0x20, 0x30, 0x42, 0x10, 0x35])
            else:                                          # mostly blocked: water/rock/off-map paths
                t = rnd.choice([0, 0, 0, 0x2f, 0x2f, 0x35, 0x0f, 0x1f])
            P.b(W.TERR + c, t)
            P.b(W.OVL + c, rnd.choice(OVLS) if style > 0.15 else 0)
            P.b(W.OCC + c, rnd.randint(1, NENT) if rnd.random() < (0.12 if style < 0.6 else 0.3) else 0)
            P.w(W.VIS + c * 2, rnd.choice([0, 0, 1, 1, 2, 3, rnd.randint(0, 40), 0x8000, 0xffff]))


def setup_common(P, rnd):
    for s in (0, 1):
        P.w(sidest(s) + 4, rnd.randint(0, 3))
        P.w(rec(s) + 6, rnd.choice([0, 1, 1]))
        P.w(rec(s) + 8, rnd.randint(0, 1))
        P.b(rec(s), rnd.choice([0, 0, 3]))
    P.w(W.ARMA, 1 if rnd.random() < 0.15 else 0)
    P.w(W.OPTS, rnd.choice([0, 0, 4, 8, 12, 2, 0x1f]))
    P.w(W.QSEL, rnd.choice([0, 0, rnd.randint(1, NENT)]))
    P.w(0x3d52e, rnd.randint(0, 0x7fff))
    P.w(0x3b002, rnd.randint(0, 5)); P.w(0x37eb6, rnd.randint(0, 1))


def case_f2f4(P, rnd):
    i = rnd.randrange(NENT)
    e = W.ENT + i * W.ESZ
    cell = rand_cell(rnd)
    setup_common(P, rnd)
    rand_entities(P, rnd, cell, i)
    rand_hood(P, rnd, cell, 7)
    P.b(e, 2)
    P.b(e + 1, rnd.randint(0, 1))
    P.b(e + 2, rnd.choice([0, 1, 1, 2, 2, 3, 3, 4, 4, 4, 5]))
    P.w(e + 8, cell)
    P.w(e + 10, rnd.choice([W.ring(P.m, rnd.randint(0, 8)), rnd.randint(-70, 70) & 0xffff]))
    if rnd.random() < 0.3: P.b(W.OCC + cell, i + 1)
    side = P.m[e + 1]
    if rnd.random() < 0.5:
        P.w(sidest(side) + 4, rnd.choice([2, 3]))
    return e, i


def case_f6b2(P, rnd):
    i = rnd.randrange(NENT)
    e = W.ENT + i * W.ESZ
    cell = rand_cell(rnd)
    setup_common(P, rnd)
    rand_entities(P, rnd, cell, i)
    rand_hood(P, rnd, cell, 2)
    P.b(e, 2)
    side = rnd.randint(0, 1)
    P.b(e + 1, side)
    P.w(e + 8, cell)
    P.b(e + 21, rnd.choice([W.dirw(P.m, rnd.randint(0, 7)), W.dirw(P.m, rnd.randint(0, 7)),
                            rnd.randint(0, 255)]))
    st = sidest(side)
    P.w(st, rnd.choice([0, 0, i + 1, i + 1, rnd.randint(1, NENT)]))
    P.w(st + 2, rnd.choice([cell, near(rnd, cell, 2), near(rnd, cell, 20), rnd.randint(0, 0xfff)]))
    if rnd.random() < 0.4:
        j = rnd.choice([rnd.randrange(NENT), i])
        t = W.ENT + j * W.ESZ
        P.l(e + 14, t)
        if rnd.random() < 0.3: P.w(t + 8, cell)
    return e, i


def cov_key(routine):
    if routine == 0xf2f4:
        return 'm%d:%s' % (W.INFO['mode'], W.INFO['cat'])
    return '%s/%s%s' % (W.INFO.get('who'), W.INFO.get('how'),
                        ('/' + W.INFO['post']) if 'post' in W.INFO else '')


def main():
    N = int(sys.argv[1]) if len(sys.argv) > 1 else 50
    rnd = random.Random(int(sys.argv[2]) if len(sys.argv) > 2 else 4321)
    tot, cov, fails = {}, {}, []
    for snap in SNAPS:
        a7, d0pre = get_a7(snap)
        m = bytearray(hx.load(S + snap))
        P = Poker(m)
        lines, cases = [], []
        for routine, mk in ((0xf2f4, case_f2f4), (0xf6b2, case_f6b2)):
            for _ in range(N):
                e, i = mk(P, rnd)
                P.l(a7, e); P.w(a7 + 4, i)
                lines += P.flush()
                cases.append((routine, e, i, bytes(m)))
                lines.append('callcap %x 400000 -' % routine)
        out = repl(snap, lines)
        blocks = re.split(r'--- callcap \$', out)[1:]
        assert len(blocks) == len(cases), (snap, len(blocks), len(cases), out[-2000:])
        for (routine, e, i, pre), blk in zip(cases, blocks):
            real = {}
            for a, x0, x1 in re.findall(r'mem \$([0-9a-f]{6}) \$([0-9a-f]{2})->\$([0-9a-f]{2})', blk):
                a = int(a, 16)
                if a7 - 0x400 <= a < a7 + 8: continue
                real[a] = int(x1, 16)
            ok_run = 'returned' in blk.split('\n')[0]
            d0m = re.search(r'D0 \$[0-9a-f]{8}->\$([0-9a-f]{8})', blk)
            rd0 = (int(d0m.group(1), 16) if d0m else d0pre) & 0xffff
            mm = bytearray(pre)
            fn = W.scan_f2f4 if routine == 0xf2f4 else W.magnet_f6b2
            ret = fn(mm, e, i) & 0xffff
            model = {a: mm[a] for a in range(len(mm)) if mm[a] != pre[a]}
            good = ok_run and model == real and rd0 == ret
            k = cov_key(routine)
            cov.setdefault(routine, {}).setdefault(k, 0); cov[routine][k] += 1
            t = tot.setdefault((routine, snap), [0, 0]); t[0 if good else 1] += 1
            if not good and len(fails) < 20:
                fails.append((hex(routine), snap, hex(e), i, 'real d0 %x model %x' % (rd0, ret),
                              {hex(a): v for a, v in real.items() if model.get(a) != v},
                              {hex(a): v for a, v in model.items() if real.get(a) != v},
                              blk.split('\n')[0][:120], k))
    byr = {}
    for (routine, snap), (g, b) in sorted(tot.items()):
        print('%06x %-16s match %4d / %4d' % (routine, snap, g, g + b))
        x = byr.setdefault(routine, [0, 0]); x[0] += g; x[1] += g + b
    for routine, (g, n) in sorted(byr.items()):
        print('TOTAL %06x  %d/%d' % (routine, g, n))
    for routine, d in sorted(cov.items()):
        print('coverage %06x' % routine, ' '.join('%s:%d' % kv for kv in sorted(d.items())))
    for f in fails:
        print('FAIL', f)


if __name__ == '__main__':
    main()
