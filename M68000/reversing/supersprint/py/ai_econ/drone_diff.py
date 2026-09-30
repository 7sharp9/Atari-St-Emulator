"""drone_diff.py - differential test: drone_model.eaea (Python) vs the real 68000 `$eaea` under `callcap`.

    cd M68000 && python3 reversing/supersprint/py/ai_econ/drone_diff.py [--samples 24] [--seed 1] [--snap <path>]

Start state: data/prerace_k.snap (make it with prerace.py: paused at $c156, the first cap write of the race
start).  The race is then run naturally (human holds fire) and, every `--stride` steps, the A4 array window and the
waypoint table are dumped and `$eaea` is callcap'd for every car slot 0..3 under 5 variants (natural, stun timer
poked, car parked just before a crossing plane / a fork / branch / jump record, spin-out accumulator + flag poked,
velocity/drift/speed poked).  The routine's argument is the word at the entry SP (8(A6) after `link`), poked and
restored around each call.  Match criterion: the set of changed bytes inside the A4 window equals the model's, byte
for byte, and the call returned.  Reports N/N.
"""
import argparse
import random

import drone_model as dm
from aiutil import *

ap = argparse.ArgumentParser()
ap.add_argument('--samples', type=int, default=24)
ap.add_argument('--stride', type=int, default=400_000)
ap.add_argument('--seed', type=int, default=1)
ap.add_argument('--snap', default=os.path.join(DATA, 'prerace_k.snap'))
ap.add_argument('--variants', default='01234')
a = ap.parse_args()
rnd = random.Random(a.seed)

LO, HI = A4 - 4200, A4 - 3600            # per-car arrays
EX = [(A4 - 1840, A4 - 1816)]           # -1832 branch table


def dump(r, lo, hi):
    b = r.mem(lo, hi - lo)
    return {lo + i: b[i] for i in range(len(b))}


def get_window(r):
    base = dump(r, LO, HI)
    for lo, hi in EX:
        base.update(dump(r, lo, hi))
    m0 = dm.Mem(base)
    tbl = m0.rl(A4 - 4084)
    cnt = m0.rw(A4 - 4076)
    base.update(dump(r, tbl, tbl + cnt * 8 + 16))
    return base, tbl, cnt


def callcap(r, car, sp0):
    """poke the argument, run callcap, restore the poked longword; return (returned?, {addr:(old,new)})"""
    orig = r.mem(sp0, 4)
    r.cmd('w %x %08x' % (sp0, (car << 16) | (orig[2] << 8) | orig[3]))
    out, _ = r.cmd('callcap eaea 20000 - A4=%x' % A4)
    r.cmd('w %x %s' % (sp0, orig.hex()))
    ok = any('returned' in l for l in out if l.startswith('--- callcap'))
    d = {}
    for l in out:
        mm = re.match(r'mem \$([0-9a-f]+) \$([0-9a-f]+)->\$([0-9a-f]+)', l)
        if mm:
            ad = int(mm.group(1), 16)
            if LO <= ad < HI:
                d[ad] = (int(mm.group(2), 16), int(mm.group(3), 16))
    return ok, d


def poke_words(r, base, pokes):
    """pokes: {addr: signed word}; returns list of (longword addr, original 4 bytes) to undo; updates base."""
    undo = {}
    for ad, v in pokes.items():
        v &= 0xFFFF
        base[ad] = v >> 8
        base[ad + 1] = v & 0xFF
    for la in sorted({ad & ~3 for ad in pokes} | {(ad + 1) & ~3 for ad in pokes}):
        if la not in undo:
            undo[la] = None
    return undo


def apply(r, base, pokes):
    orig = {}
    for ad in pokes:
        for la in (ad & ~3, (ad + 1) & ~3):
            if la not in orig:
                orig[la] = r.mem(la, 4)
    for ad, v in pokes.items():
        v &= 0xFFFF
        base[ad] = v >> 8
        base[ad + 1] = v & 0xFF
    for la in orig:
        r.cmd('w %x %02x%02x%02x%02x' % (la, base[la], base[la + 1], base[la + 2], base[la + 3]))
    return orig


def restore(r, base, orig):
    for la, b in orig.items():
        r.cmd('w %x %s' % (la, b.hex()))
        for i in range(4):
            base[la + i] = b[i]


def variant_pokes(v, car, base, tbl, cnt, flagged):
    m = dm.Mem(base)
    P = {}
    A = lambda off: dm.arr(off, car)
    if v == 1:
        P[A(-3810)] = rnd.randint(1, 12)
        P[A(-3730)] = rnd.randint(0, 130)
    elif v == 2:
        cap = m.rw(A(-3874))
        real = [i for i in range(cnt) if dm.record(m, i)[3] & ~0xF == 0 and dm.record(m, i) != [0, 0, 0, 0]]
        if flagged and rnd.random() < 0.6:
            wp = rnd.choice(flagged) - 2
        else:
            wp = rnd.choice(real)
        rec = dm.record(m, wp)
        h = rec[3] & 0xF
        tx = rec[0] + dm.s16(rec[2] * m.rw(dm.A4 - 4118 + 2 * h))
        ty = rec[1] + dm.s16(rec[2] * m.rw(dm.A4 - 4150 + 2 * h))
        side = rnd.choice([-3, -1, 0, 1, 2, 5])
        q = ((h + 2) & 15) >> 2
        px = tx + (side if q in (1, 3) else rnd.randint(-20, 20))
        py = ty + (side if q in (0, 2) else rnd.randint(-20, 20))
        P[A(-3802)] = wp
        P[A(-3714)] = h
        P[A(-3962)] = tx
        P[A(-3970)] = ty
        P[A(-3738)] = px
        P[A(-3746)] = py
        P[A(-3730)] = rnd.randint(0, cap + 6)
        P[A(-3810)] = 0
    elif v == 5:
        # gate/branch record: poke the record after `wp` to 0x200|k, and the branch table entry k to 2/3/4/0
        real = [i for i in range(cnt - 8) if dm.record(m, i)[3] & ~0xF == 0 and dm.record(m, i) != [0, 0, 0, 0] and i % 2 == 0]
        wp = rnd.choice(real)
        nxt = wp + 2
        k = rnd.randint(0, 3)
        rec = dm.record(m, wp)
        h = rec[3] & 0xF
        tx = rec[0] + dm.s16(rec[2] * m.rw(dm.A4 - 4118 + 2 * h))
        ty = rec[1] + dm.s16(rec[2] * m.rw(dm.A4 - 4150 + 2 * h))
        q = ((h + 2) & 15) >> 2
        P[tbl + 8 * nxt + 6] = 0x200 | k
        P[dm.A4 - 1832 + 2 * k] = rnd.choice([2, 3, 4, 0, 1])
        P[A(-3802)] = wp
        P[A(-3714)] = h
        P[A(-3962)] = tx
        P[A(-3970)] = ty
        P[A(-3738)] = tx + (2 if q in (1, 3) else 0)
        P[A(-3746)] = ty + (2 if q in (0, 2) else 0)
        P[A(-3810)] = 0
        P[A(-3730)] = rnd.randint(0, 100)
    elif v == 3:
        P[A(-3866)] = rnd.randint(0, 40)
        P[A(-3826)] = rnd.choice([0, 0x400, 0x30, 0x430, 0x1])
        P[A(-3706)] = rnd.randint(0, 15)
        P[A(-3810)] = 0
    elif v == 4:
        P[A(-3978)] = rnd.randint(-300, 300)
        P[A(-3986)] = rnd.randint(-300, 300)
        P[A(-3994)] = rnd.randint(-400, 400)
        P[A(-4002)] = rnd.randint(-400, 400)
        P[A(-3730)] = rnd.randint(0, 140)
        P[A(-3810)] = rnd.choice([0, 0, 3])
    return P


def main():
    r = Repl2(a.snap)
    out, regs = r.cmd('')
    sp0 = regs['A7']
    r.cmd('kbd fe 80')
    tot = ok = 0
    per_variant = {}
    branch_seen = {}
    bad = []
    for smp in range(a.samples):
        r.cmd('s %d' % a.stride)
        _, regs = r.cmd('')
        sp0 = regs['A7']
        base, tbl, cnt = get_window(r)
        flagged = [i for i in range(cnt) if dm.record(dm.Mem(base), i)[3] & ~0xF]
        for car in range(4):
            for v in [int(c) for c in a.variants]:
                b2 = dict(base)
                P = variant_pokes(v, car, b2, tbl, cnt, flagged)
                orig = apply(r, b2, P)
                m = dm.Mem(b2)
                tr = []
                dm.eaea(m, car, tr)
                exp = {ad: ov for ad, ov in m.delta().items() if LO <= ad < HI}
                good, act = callcap(r, car, sp0)
                restore(r, b2, orig)
                tot += 1
                per_variant.setdefault(v, [0, 0])[1] += 1
                if good and exp == act:
                    ok += 1
                    per_variant[v][0] += 1
                    for e in set(tr):
                        branch_seen[e] = branch_seen.get(e, 0) + 1
                else:
                    bad.append((smp, car, v, good, sorted(set(exp) ^ set(act))[:6], [(hex(k), exp.get(k), act.get(k)) for k in sorted(set(exp) | set(act)) if exp.get(k) != act.get(k)][:6]))
        print('sample %d: cumulative %d/%d' % (smp, ok, tot), flush=True)
    print('RESULT %d/%d states match (changed-byte sets identical)' % (ok, tot))
    print('per variant', per_variant, 'branch coverage', branch_seen)
    for b in bad[:12]:
        print('MISMATCH', b)
    r.close()


main()
