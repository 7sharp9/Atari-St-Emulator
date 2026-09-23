"""fdiff.py [N_per_snap] [seed] - randomized callcap diff of the walker-triggered AI land edits.

  $f6b2  walker_choose_dir_magnet: full non-stack memory delta + D0.w vs ai_ext.f6b2
         (knights with a valid target included; a knight whose target is invalid calls $fe00
          and is not generated)
  $ef4c  walker_step: god-record delta ($21e0c..$21e67) vs [real $f6b2/$f2f4 god-rec writes and
         D0 (oracle, callcap'd from the same state)] + ai_ext.ef4c_lower

States (pattern of reversing/populous/py/ai_diff.py): per case a walker gets a random side, cell,
last direction, knight target; its side a random leader/magnet/mode; both god records random
ctrl/busy; random game flags, armageddon flag, and a 5x5 terrain-class patch around the walker
(water, rock, swamp, burnt, land) plus the class of the leader's/target's cell.
"""
import os, random, re, sys
from aicfg import *
import ai_ref as A
import ai_ext as X
import hx
from ai_diff import Poker
import subprocess


def repl(snap, lines):
    env = dict(os.environ, ATARI_NOTRACE='1')
    p = subprocess.run(['dotnet', 'exec', DLL, 'resume', snap, 'repl', '--disk-a', DISK],
                       input='\n'.join(lines + ['q']) + '\n', capture_output=True, text=True, cwd=R, env=env)
    return p.stdout + p.stderr


def get_a7(snap):
    out = repl(snap, ['r'])
    return (int(re.search(r'A7:([0-9a-f]{8})', out).group(1), 16),
            int(re.search(r'D0:([0-9a-f]{8})', out).group(1), 16))

SNAPS = [P('cg1.snap'), P('cg2.snap'), os.path.join(WORK, 'g90.snap')]
CLASSES = [0, 0, 0x2f, 0x35, 0x35, 0x42, 0x42, 0x0f, 0x0f, 0x1f, 0x20, 0x0f]
DIRS = [-64, -63, 1, 65, 64, 63, -1, -65]


def gen(P_, rnd, m, n):
    i = rnd.randrange(n)
    wp = A.WALK + i * A.WSZ
    side = rnd.randint(0, 1)
    x, y = rnd.randint(0, 63), rnd.randint(0, 63)
    if rnd.random() < 0.8:
        x, y = rnd.randint(2, 61), rnd.randint(2, 61)
    cell = y * 64 + x
    P_.b(wp + 0, 2); P_.b(wp + 1, side); P_.w(wp + 4, rnd.randint(1, 5000)); P_.w(wp + 8, cell)
    P_.b(wp + 21, rnd.choice(DIRS + [0]) & 0xff)
    P_.l(wp + 14, 0)
    st, r = A.sidest(side), A.rec(side)
    # other walkers used as leader / knight target
    others = [j for j in range(n) if j != i]
    j = rnd.choice(others)
    op = A.WALK + j * A.WSZ
    tcell = rnd.choice([cell, rnd.randint(0, 0xfff),
                        cell + rnd.choice(DIRS) * rnd.randint(1, 5)]) & 0xfff
    P_.w(op + 8, tcell); P_.w(op + 4, rnd.randint(1, 5000))
    kind = rnd.random()
    if kind < 0.2:                                           # knight with a valid target
        P_.b(op + 1, 1 - side); P_.b(op + 0, rnd.choice([1, 2]))
        if tcell == cell: P_.w(op + 8, (cell + 1) & 0xfff)
        P_.l(wp + 14, op)
    P_.w(st + 0, rnd.choice([0, 0, i + 1, j + 1]))
    P_.w(st + 2, rnd.choice([cell, tcell, rnd.randint(0, 0xfff), (cell + rnd.choice(DIRS)) & 0xfff]))
    P_.w(st + 4, rnd.choice([0, 0, 1, 2, 3]))
    for s in (0, 1):
        P_.w(A.rec(s) + 6, rnd.choice([0, 1, 1]))
        P_.w(A.rec(s) + 8, rnd.choice([0, 0, 1]))
        P_.b(A.rec(s), rnd.choice([0, 0, 1, 2, 5, 14]))
    P_.w(A.FLAGS, rnd.choice([0, 0, 0, 4, 8, 0xc, 1, 2, 0x10, 3]))
    P_.w(X.ARMA, rnd.choice([0] * 8 + [1]))
    P_.w(X.QUERY, rnd.choice([0, 0, 5]))
    P_.w(A.SEED, rnd.randint(0, 0x7fff))
    pal = rnd.choice([CLASSES, CLASSES, [0, 0x2f, 0x35], [0, 0, 0, 0x0f], [0x35, 0x35, 0x0f, 0x42]])
    for dy in range(-2, 3):
        for dx in range(-2, 3):
            px, py = x + dx, y + dy
            if 0 <= px < 64 and 0 <= py < 64:
                P_.b(X.MAP + py * 64 + px, rnd.choice(pal))
    if rnd.random() < 0.3:
        P_.b(X.MAP + cell, rnd.choice([0x42, 0x0f]))
    return wp, i


def main():
    N = int(sys.argv[1]) if len(sys.argv) > 1 else 200
    rnd = random.Random(int(sys.argv[2]) if len(sys.argv) > 2 else 99)
    tot = {}; cov = {}; fails = []
    for snap in SNAPS:
        a7, d0pre = get_a7(snap)
        m = bytearray(hx.load(snap))
        n = A.rw(m, 0x3c4e2)
        P_ = Poker(m)
        lines, cases = [], []
        for routine in (0xf6b2, 0xef4c):
            for k in range(N):
                wp, i = gen(P_, rnd, m, n)
                P_.l(a7, wp); P_.w(a7 + 4, i)
                lines += P_.flush()
                pre = bytes(m)
                if routine == 0xef4c:
                    inner = 0xf6b2 if X.ef4c_uses_f6b2(pre, wp) else 0xf2f4
                    lines.append('callcap %x 400000 -' % inner)
                else:
                    inner = None
                lines.append('callcap %x 2000000 -' % routine)
                cases.append((routine, wp, i, pre, inner))
        out = repl(snap, lines)
        blocks = re.split(r'--- callcap \$', out)[1:]
        need = sum(2 if c[4] else 1 for c in cases)
        assert len(blocks) == need, (snap, len(blocks), need)
        bi = 0
        for routine, wp, i, pre, inner in cases:
            iblk = None
            if inner:
                iblk = blocks[bi]; bi += 1
            blk = blocks[bi]; bi += 1

            def delta(b):
                d = {}
                for a, _x0, x1 in re.findall(r'mem \$([0-9a-f]{6}) \$([0-9a-f]{2})->\$([0-9a-f]{2})', b):
                    a = int(a, 16)
                    if a7 - 0x1000 <= a < a7 + 8: continue
                    d[a] = int(x1, 16)
                return d

            def d0(b):
                mm_ = re.search(r'D0 \$[0-9a-f]{8}->\$([0-9a-f]{8})', b)
                return int(mm_.group(1), 16) & 0xffff if mm_ else None
            ok_run = 'returned' in blk.split('\n')[0]
            mm = bytearray(pre)
            if routine == 0xf6b2:
                try:
                    ret = X.f6b2(mm, wp, i)
                except X.NotModelled:
                    continue
                real = delta(blk)
                model = {a: mm[a] for a in range(len(mm)) if mm[a] != pre[a]}
                rd0 = d0(blk)
                if rd0 is None: rd0 = d0pre & 0xffff   # regdelta omits an unchanged D0
                good = ok_run and real == model and A.s16(rd0) == A.s16(ret)
                oc = 'dir999' if ret == 999 else 'dir'
                side = pre[wp + 1]; rr = A.rec(side)
                if X.LAST: oc += '+' + X.LAST
                if A.rw(mm, A.sidest(side)) != A.rw(pre, A.sidest(side)): oc += '+leader'
                if A.rl(pre, wp + 14): oc += '+knight'
            else:
                for a, v in delta(iblk).items():
                    if 0x21e0c <= a < 0x21e68: mm[a] = v
                dv = d0(iblk)
                if dv is None: dv = d0pre & 0xffff
                X.ef4c_lower(mm, wp, dv)
                real = {a: v for a, v in delta(blk).items() if 0x21e0c <= a < 0x21e68}
                model = {a: mm[a] for a in range(0x21e0c, 0x21e68) if mm[a] != pre[a]}
                good = ok_run and 'returned' in iblk.split('\n')[0] and real == model
                side = pre[wp + 1]; rr = A.rec(side)
                oc = 'inner_%x' % inner
                if X.LAST: oc += '+' + X.LAST
                elif model: oc += '+inner_godrec'
            cov.setdefault(routine, {}).setdefault(oc, 0); cov[routine][oc] += 1
            t = tot.setdefault((routine, os.path.basename(snap)), [0, 0]); t[0 if good else 1] += 1
            if not good and len(fails) < 20:
                fails.append((hex(routine), os.path.basename(snap), hex(wp), i,
                              {hex(k): v for k, v in sorted(real.items())},
                              {hex(k): v for k, v in sorted(model.items())}, blk.split('\n')[0]))
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
