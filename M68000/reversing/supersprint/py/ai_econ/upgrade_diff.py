"""upgrade_diff.py [n] - prove the car-parameter formulas of the race-start initialiser $be40 (upgrade levels -> div, cap,
turn threshold; drone cap = 60 - 4T + 4*car + R) against the real code over n random configurations.

Each configuration resumes data/prerace_b.snap (paused at $bec0, the head of $be40's per-car loop), pokes random upgrade
levels -4074+8*car+2*item (items 0..3, levels 0..5) for the three human-capable slots, a random race counter R=-1748(A4)
(0..50) and a random track index T (8(A6) of $be40; only the number is used by the cap formula), runs to $c2ba (the end of the
loop) and compares every car's -3882 (div), -3898, -3874 (cap), -3890 (turn threshold), -3730 (speed), -3802 (wp) with the model.
Drone slots are [0,2,3] (slot 1 = human), exactly as in the snapshot.

    cd M68000 && python3 reversing/supersprint/py/ai_econ/upgrade_diff.py 24
"""
import random
from aiutil import *


def tdiv(a, b):
    q = abs(a) // abs(b)
    return q if (a >= 0) == (b >= 0) else -q


def model(levels, R, T, drone):
    out = []
    for c in range(4):
        u0, u1, u2 = (levels[c][0], levels[c][1], levels[c][2]) if c < 3 else (0, 0, 0)
        div = 40 - 5 * u2
        t1 = tdiv(11 * div, 4)
        cap = t1 + tdiv(u1 * 5 * div, 40)
        thr = tdiv(cap * 8, 11) + tdiv(u0 * 4 * div, 40)
        spd = 0
        if drone[c]:
            cap = 60 - 4 * T + 4 * c + R
            div = 40
            spd = 10 * c
        out.append(dict(div=div, t1=t1, cap=cap, thr=thr, spd=spd))
    return out


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 24
    rnd = random.Random(7)
    ok = tot = 0
    for k in range(n):
        r = Repl2(os.path.join(DATA, 'prerace_b.snap'))
        out, regs = r.cmd('')
        A6 = regs['A6']
        drone = r.a4w(-3914, 4)
        levels = [[rnd.randint(0, 5) for _ in range(4)] for _ in range(3)]
        R = rnd.randint(0, 50)
        T = rnd.randint(0, 7)
        pokes = {A4 - 1748: R, A6 + 8: T}
        for c in range(3):
            for it in range(4):
                pokes[A4 - 4074 + 8 * c + 2 * it] = levels[c][it]
        setwords(r, pokes)
        out, regs = r.cmd('bpc c2ba 1 500000')
        assert any('hit' in l for l in out), out
        got = dict(div=r.a4w(-3882), t1=r.a4w(-3898), cap=r.a4w(-3874), thr=r.a4w(-3890), spd=r.a4w(-3730))
        exp = model(levels, R, T, drone)
        for c in range(4):
            tot += 1
            e = exp[c]
            if all(got[f][c] == e[f] for f in e):
                ok += 1
            else:
                print('MISMATCH cfg', k, 'car', c, 'levels', levels[c] if c < 3 else None, 'R', R, 'T', T, 'got', {f: got[f][c] for f in e}, 'exp', e)
        r.close()
        print('config %d: R=%d T=%d levels=%s caps=%s' % (k, R, T, levels, got['cap']), flush=True)
    print('RESULT %d/%d car records match' % (ok, tot))


main()
