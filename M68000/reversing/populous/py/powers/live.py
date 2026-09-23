"""live.py - check powers_ref against the real code on every natural call in a played run.

usage: python live.py <start.snap> <frames> <kind> [<kind> ...]
kinds:
  retarget  bp $f6ca (walker_choose_dir_magnet, after A5 = walker): for a knight (+14 != 0) the model
            predicts whether $fe00 is called (target cell reached / str <= 0 / same side / ruin) and
            its result; compared with the whole DATA/BSS region at $f716.
  merge     bp $feca .. $10066: walker_merge(i, j), full compare.
  resolve   bp $108b8 .. $10e7c: combat_resolve(w, l), full compare for the modelled paths
            (walker loser; knight winner vs settlement = raze); take-overs are counted, not compared.
Each kind is a separate pass over the same deterministic trajectory (breakpoints do not change it).
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pwlib import *
import powers_ref as P

LO, HI = 0x21464, 0x3d560
TMP = os.path.join(PD, 'snaps', 'tmp')
KINDS = {'retarget': (0xf6ca, 0xf716), 'merge': (0xfeca, 0x10066), 'resolve': (0x108b8, 0x10e7c)}


def keep(a, a7):
    return not (a7 - 0x1000 <= a < a7 + 0x100) and not (0x37f5a <= a < 0x37f8a)


def run(start, frames, kind):
    os.makedirs(TMP, exist_ok=True)
    fe, fx = os.path.join(TMP, kind + '_e.snap'), os.path.join(TMP, kind + '_x.snap')
    ent, ex = KINDS[kind]
    r = Repl2(start)
    f0 = int.from_bytes(r.mem(P.FRAME, 2), 'big')
    stats = {}
    fails = []
    events = []
    while True:
        out, rg = r.cmd('bp %x 2000000' % ent)
        fr = int.from_bytes(r.mem(P.FRAME, 2), 'big')
        if (fr - f0) & 0xffff >= frames:
            break
        if rg.get('PC') != ent:
            continue
        a7 = rg['A7']
        if kind == 'retarget':
            a5 = rg['A5']
            if not int.from_bytes(r.mem(a5 + 14, 4), 'big'):
                r.cmd('s 1'); continue
        r.cmd('snap ' + fe)
        r.cmd('u %x 3000000' % ex)
        r.cmd('snap ' + fx)
        pre, post = ram(fe), ram(fx)
        mm = bytearray(pre)
        sys.setrecursionlimit(100000)
        tag = kind
        if kind == 'retarget':
            k = rg['A5']
            t = P.rl(mm, k + 14) & 0xffffff
            cond = (P.rw(mm, k + 8) == P.rw(mm, t + 8) or P.rw(mm, t + 4) <= 0 or
                    P.rb(mm, t + 1) == P.rb(mm, k + 1) or P.rb(mm, t) & 0x80)
            if cond:
                P.knight_find_target(mm, k)
            tag = 'retarget_call' if cond else 'retarget_keep'
            events.append((fr, (k - P.ENT) // 0x16, P.rw(pre, k + 8), (t - P.ENT) // 0x16, (P.rl(mm, k + 14) - P.ENT) // 0x16))
        elif kind == 'merge':
            i, j = P.rw(pre, a7 + 4), P.rw(pre, a7 + 6)
            kn = P.rl(pre, P.ent(i) + 14) != 0
            tag = 'merge_knight_into_town' if kn and P.rb(pre, P.ent(j)) == 1 else 'merge_knight' if kn else 'merge'
            P.walker_merge(mm, i, j)
            events.append((fr, i, j, tag))
        else:
            w, l = P.rw(pre, a7 + 4), P.rw(pre, a7 + 6)
            W, L = P.ent(w), P.ent(l)
            town = P.rb(pre, L) & 1
            kn = P.rl(pre, W + 14) != 0
            events.append((fr, w, l, 'town' if town else 'walker', 'knight' if kn else ''))
            if town and not kn:
                stats.setdefault('resolve_takeover_unmodelled', [0, 0])[1] += 1
                continue
            tag = 'raze' if town else 'resolve_walker' + ('_knightwin' if kn else '')
            P.combat_resolve(mm, w, l)
        bad = [a for a in range(LO, HI) if keep(a, a7) and post[a] != mm[a]]
        s = stats.setdefault(tag, [0, 0]); s[1] += 1
        if not bad:
            s[0] += 1
        elif len(fails) < 5:
            fails.append((tag, fr, [(hex(a), pre[a], post[a], mm[a]) for a in bad[:10]]))
    r.close()
    return stats, fails, events, f0


if __name__ == '__main__':
    start, frames = sys.argv[1], int(sys.argv[2])
    for kind in sys.argv[3:]:
        stats, fails, events, f0 = run(start, frames, kind)
        print(kind, 'frames %d..%d' % (f0, f0 + frames), stats)
        for e in events[:60]:
            print('  ', e)
        for f in fails:
            print('  FAIL', f)
