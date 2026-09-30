"""winner_diff.py [n] [n_full] - reconstruct the WINNER'S CIRCLE ranking/statistics ($1a4ca up to $1ad40) and the
post-results elimination rule (up to its `rts` at $1b3b6) and compare with the real routine on n random race-result states.

Start: data/pre_winner.snap (pre_winner.py: entry of $1a4ca after a real race).  Each state: new process, poke
lap counters -3906, checkpoint idx -3850, tile counters -3842, drone flags -3914, lap-time stamps -3946[car][lap], the race timer
-8072, R=-1748 and the track word (12(A6)); run to $1ad40 (after the sort and the statistics loop; ~350k steps) and compare
the locals rank[-70(A6)], inverse rank[-62], keys[-54], best lap[-78], average lap[-86], par-avg bar[-102], par-best bar[-94],
the converted lap array -3946, the record -8066+2T and R with the model.  For the first n_full states also run on to `rts`
($1b3b6, ~8M steps, includes the animation) and compare the drone flags, wrenches and upgrade levels (elimination).
"""
import random
from aiutil import *


def s16(v):
    v &= 0xFFFF
    return v - 0x10000 if v & 0x8000 else v


def tdiv(a, b):
    q = abs(a) // abs(b)
    return q if (a >= 0) == (b >= 0) else -q


def model(lap, chk, tiles, drone, L, timer, T, rec, R, wr, lv):
    L = [row[:] for row in L]
    for c in range(4):
        for l in (3, 2, 1):
            L[c][l] = s16(L[c][l] - L[c][l - 1])
    S = [lap[c] * 100000 + chk[c] * 10000 + tiles[c] for c in range(4)]
    rank = [0, 1, 2, 3]
    while True:
        flag = True
        for i in range(3):
            a, b = rank[i], rank[i + 1]
            if S[a] < S[b]:
                rank[i], rank[i + 1] = b, a
                flag = False
            elif S[a] == S[b] and drone[a] == 1 and drone[b] == 0:
                rank[i], rank[i + 1] = b, a
                flag = False
        if flag:
            break
    if drone[rank[0]] == 1:
        R -= 1
    inv = [0] * 4
    for i in range(4):
        inv[rank[i]] = i
    best, avg, barA, barB = [0] * 4, [0] * 4, [0] * 4, [0] * 4
    rec = rec[:]
    par = (T + 15) * 50
    for c in range(4):
        n = lap[c]
        if n == 0:
            L[c][0] = timer
            n = 1
        b, s = 10000, 0
        for l in range(n):
            b = min(b, L[c][l])
            s = s16(s + L[c][l])
        a = tdiv(s, n)
        best[c], avg[c] = b, a
        if drone[c] == 0 and b < rec[T]:
            rec[T] = b
        x = par - a if par > a else 0
        y = par - b if par > b else 0
        barA[c] = x - (x % 10)
        barB[c] = y - (y % 10)
    # elimination (after the animation)
    d2 = drone[:]
    for i in range(3):
        if d2[rank[i]] == 1:
            for j in range(i, 4):
                d2[rank[j]] = 1
            break
    wr2 = wr[:]
    lv2 = [row[:] for row in lv]
    for i in range(3):
        if d2[i] == 1:
            wr2[i] = 0
            lv2[i] = [0, 0, 0, 0]
    return dict(rank=rank, inv=inv, keys=S, best=best, avg=avg, barA=barA, barB=barB, L=L, R=R, rec=rec, drone_after=d2, wr_after=wr2, lv_after=lv2)


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 30
    nfull = int(sys.argv[2]) if len(sys.argv) > 2 else 4
    rnd = random.Random(3)
    ok = tot = 0
    for k in range(n):
        lap = [rnd.choice([0, 1, 2, 3, 3, 4, 4]) for _ in range(4)]
        if rnd.random() < 0.5:
            lap[rnd.randrange(4)] = lap[rnd.randrange(4)]       # provoke ties
        chk = [rnd.randint(0, 5) for _ in range(4)]
        tiles = [rnd.randint(0, 99) for _ in range(4)]
        if rnd.random() < 0.4:                                   # exact key ties between a drone and a human
            chk[2], tiles[2], lap[2] = chk[0], tiles[0], lap[0]
        drone = [rnd.randint(0, 1) for _ in range(3)] + [1]
        T = rnd.randint(0, 7)
        timer = rnd.randint(300, 3000)
        L = []
        for c in range(4):
            t, row = 0, []
            for l in range(4):
                if l < lap[c]:
                    t += rnd.randint(300, 900)
                    row.append(t)
                else:
                    row.append(0)
            L.append(row)
        R0 = rnd.randint(0, 20)
        wr = [rnd.randint(0, 6) for _ in range(3)]
        lv = [[rnd.randint(0, 5) for _ in range(4)] for _ in range(3)]
        rec0 = [rnd.randint(200, 3000) for _ in range(8)]
        r = Repl2(os.path.join(DATA, 'pre_winner.snap'))
        out, regs = r.cmd('')
        sp = regs['A7']
        pokes = {sp + 8: T, A4 - 1748: R0}
        for c in range(4):
            pokes[A4 - 3906 + 2 * c] = lap[c]
            pokes[A4 - 3850 + 2 * c] = chk[c]
            pokes[A4 - 3842 + 2 * c] = tiles[c]
            pokes[A4 - 3914 + 2 * c] = drone[c]
            for l in range(4):
                pokes[A4 - 3946 + 8 * c + 2 * l] = L[c][l]
        pokes[A4 - 8072] = timer
        for c in range(3):
            pokes[A4 - 3954 + 2 * c] = wr[c]
            for it in range(4):
                pokes[A4 - 4074 + 8 * c + 2 * it] = lv[c][it]
        for t in range(8):
            pokes[A4 - 8066 + 2 * t] = rec0[t]
        setwords(r, pokes)
        out, regs = r.cmd('bp 1ad40 10000000')
        assert any('hit' in l for l in out), out
        A6 = regs['A6']
        got = dict(rank=r.words(A6 - 70, 4), inv=r.words(A6 - 62, 4), keys=list(struct.unpack('>4i', r.mem(A6 - 54, 16))),
                   best=r.words(A6 - 78, 4), avg=r.words(A6 - 86, 4), barA=r.words(A6 - 102, 4), barB=r.words(A6 - 94, 4),
                   L=[r.a4w(-3946 + 8 * c, 4) for c in range(4)], R=r.a4w(-1748, 1)[0], rec=r.a4w(-8066, 8))
        exp = model(lap, chk, tiles, drone, L, timer, T, rec0, R0, wr, lv)
        fields = ['rank', 'inv', 'keys', 'best', 'avg', 'barA', 'barB', 'L', 'R', 'rec']
        good = all(got[f] == exp[f] for f in fields)
        tot += 1
        ok += good
        if not good:
            print('MISMATCH', k, {f: (got[f], exp[f]) for f in fields if got[f] != exp[f]}, 'in', dict(lap=lap, chk=chk, tiles=tiles, drone=drone))
        if k < nfull:
            out, regs = r.cmd('bp 1b3b6 40000000')
            assert any('hit' in l for l in out), out
            g2 = dict(drone_after=r.a4w(-3914, 4), wr_after=r.a4w(-3954, 3), lv_after=[r.a4w(-4074 + 8 * c, 4) for c in range(3)])
            e2 = {f: exp[f] for f in g2}
            good2 = g2 == e2
            tot += 1
            ok += good2
            if not good2:
                print('MISMATCH(elimination)', k, g2, e2, 'drone_in', drone, 'rank', exp['rank'])
        r.close()
        print('state %d: %d/%d' % (k, ok, tot), flush=True)
    print('RESULT %d/%d checks match' % (ok, tot))


main()
