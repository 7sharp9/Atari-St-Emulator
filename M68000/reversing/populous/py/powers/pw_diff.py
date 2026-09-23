"""pw_diff.py - differential test: powers_ref.py vs the real routines under callcap.

For each base snapshot, N randomized states per routine are poked into one REPL session and the
real routine is run with `callcap` (JSON delta). The model runs on the same pre-state image. The
compared region is DATA+BSS [$21464, $3d560) minus the stack scratch; outside it the routines only
touch the screen buffers, TOS Setscreen variables and the pointer-hide counter in TEXT.

Earthquake: the 20 shake frames wait for the VBL ($16f0a) and callcap masks interrupts, so it is
tested in two parts: (a) callcap $12350 until the loop detector stops it in the first shake frame
(gate, cost, dirty box, sound, score, $2287a compared on the fields the pre-part writes), and
(b) callcap from $12470 (PC/A6 presets, frame built above the entry SP, sentinel return slot) on
the model's pre-state, full compare.

usage: python pw_diff.py [N] [seed] [routine-filter]
"""
import os, random, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pwlib import *
import powers_ref as P

SNAPS = ['game_start.snap', 'g90.snap', 'late4.snap']
LO, HI = 0x21464, 0x3d560
CCD = os.path.join(PD, 'cc')
SENT = 0x00dead00


TRAPSAVE = (0x37f5a, 0x37f8a)     # $2061c..$206bc trap wrappers' register save stack (4 x 12 bytes)


def _keep(a, a7):
    return LO <= a < HI and not (a7 - 0x1000 <= a < a7 + 0x100) and not (TRAPSAVE[0] <= a < TRAPSAVE[1])


def region_delta(pre, post, a7):
    return {a: post[a] for a in range(LO, HI) if pre[a] != post[a] and _keep(a, a7)}


def real_delta(pre, mem, a7):
    return {a: v for a, v in mem.items() if _keep(a, a7) and pre[a] != v}


# ------------------------------------------------------------------ randomizers
def rnd_gate(K, rnd, m, side, cost, bit):
    K.w(P.HUMAN, rnd.randint(0, 1))
    K.w(P.PAINT, 1 if rnd.random() < 0.08 else 0)
    K.w(P.PAUSE, 1 if rnd.random() < 0.06 else 0)
    K.w(P.ARMA, 1 if rnd.random() < 0.06 else 0)
    pw = rnd.getrandbits(9)
    pw = (pw | bit) if rnd.random() < 0.85 else (pw & ~bit)
    K.w(P.GOD + P.GSZ * side + 14, pw)
    c = P.rl(m, P.COST[cost])
    K.l(P.mana_a(side), rnd.choice([c - 1, c, c + rnd.randint(0, 5000), c + rnd.randint(0, 5000), c + 1, rnd.randint(-250, 2 * c)]))
    K.l(P.mana_a(1 - side), rnd.randint(-250, 90000))
    K.l(P.SCORE, rnd.randint(0, 100000))
    K.w(P.SEED, rnd.randint(0, 0x7fff))


def rnd_terrain(K, rnd, m, x0, y0, x1, y1, nops):
    """random but legal terrain in a box: apply model raise/lower ops, then scribble cell maps."""
    img = bytearray(m)
    saved = {a: img[a] for a in (list(range(P.POINTS, P.POINTS + 2)) + [b + k for b in P.BOX for k in (0, 1)])}
    for _ in range(nops):
        x, y = rnd.randint(x0, x1), rnd.randint(y0, y1)
        (P.raise_point if rnd.random() < 0.6 else P.lower_point)(img, x, y)
    for a, v in saved.items():
        img[a] = v
    for i in range(65 * 65):
        a = P.HGT + 2 * i
        if img[a:a + 2] != m[a:a + 2]:
            K.w(a, P.ruw(img, a))
    for _ in range(rnd.randint(0, 25)):
        x, y = rnd.randint(max(0, x0), min(63, x1)), rnd.randint(max(0, y0), min(63, y1))
        c = x + 64 * y
        r = rnd.random()
        if r < 0.3:
            K.b(P.SHAPE + c, rnd.choice([0x2f, 0x30, 0x31]))
        elif r < 0.5:
            K.b(P.SHAPE + c, rnd.choice([0x0f, 0x1f, 0x20, 0x42, 0x35]))
        elif r < 0.8:
            K.b(P.FEAT + c, rnd.choice([0, 0x32, 0x33, 0x34, 0x21, 0x25, 0x2a]))
        else:
            K.b(P.OCC + c, rnd.randint(0, 8))


def rnd_leaders(K, rnd, m, x, y):
    n = P.rw(m, P.NENT)
    for s in (0, 1):
        K.w(P.SIDE + 16 * s, rnd.choice([0] + list(range(1, n + 1))))
        ld = P.rw(m, P.SIDE + 16 * s)
        if ld and rnd.random() < 0.6:
            K.w(P.ent(ld - 1) + 8, (x + rnd.randint(0, 7)) % 64 + 64 * ((y + rnd.randint(0, 7)) % 64))
        mg = (x + rnd.randint(0, 7)) % 64 + 64 * ((y + rnd.randint(0, 7)) % 64) if rnd.random() < 0.5 else rnd.randint(0, 0xfff)
        K.w(P.SIDE + 16 * s + 2, mg)


def rnd_entities(K, rnd, m, nmin=1, nmax=48):
    n = rnd.randint(nmin, nmax)
    K.w(P.NENT, n)
    for i in range(n):
        e = P.ent(i)
        K.b(e, rnd.choice([1, 1, 2, 2, 2, 0x80, 8, 0x0a, 9, 0x12, 4, 0x42]))
        K.b(e + 1, rnd.randint(0, 1))
        K.w(e + 4, rnd.choice([rnd.randint(1, 900), rnd.randint(-3, 0)]))
        K.w(e + 8, rnd.randint(0, 0xfff))
        K.l(e + 14, rnd.choice([0, 0, 0, P.ent(rnd.randint(0, n - 1))]))
        K.b(e + 20, rnd.choice([0, 0, 1, 2]))
    for s in (0, 1):
        K.w(P.SIDE + 16 * s, rnd.choice([0] + list(range(1, n + 1))))
    return n


# ------------------------------------------------------------------ cases
def make_case(K, rnd, m, routine, a7):
    """poke a random state for `routine`; returns (callcap lines, model fn, pre-image, info)."""
    side = rnd.randint(0, 1)
    if routine == 'flood':
        rnd_gate(K, rnd, m, side, 'flood', 0x80)
        rnd_terrain(K, rnd, m, 0, 0, 64, 64, rnd.randint(0, 40))
        K.l(a7, side << 16)
        return ['callcap 11f6a 3000000 %s'], (lambda mm: P.flood(mm, side)), dict(side=side)
    if routine in ('volcano', 'eq'):
        x, y = (rnd.randint(0, 56), rnd.randint(0, 56)) if rnd.random() < 0.9 else (rnd.randint(50, 63), rnd.randint(50, 63))
        rnd_gate(K, rnd, m, side, 'volcano' if routine == 'volcano' else 'eq', 0x40 if routine == 'volcano' else 0x08)
        rnd_terrain(K, rnd, m, x - 2, y - 2, x + 10, y + 10, rnd.randint(0, 60))
        rnd_leaders(K, rnd, m, x, y)
        for b in P.BOX:
            K.w(b, rnd.randint(0, 63))
        K.w(P.POINTS, rnd.randint(0, 500))
        K.l(a7, (side << 16) | x); K.w(a7 + 4, y)
        if routine == 'volcano':
            return ['callcap 1263c 3000000 %s'], (lambda mm: P.volcano(mm, side, x, y)), dict(side=side, x=x, y=y)
        return 'eq', (side, x, y), dict(side=side, x=x, y=y)
    if routine == 'swamp':
        x, y = rnd.randint(0, 63), rnd.randint(0, 63)
        rnd_gate(K, rnd, m, side, 'swamp', 0x10)
        for dy in range(-3, 4):
            for dx in range(-3, 4):
                cx, cy = x + dx, y + dy
                if 0 <= cx < 64 and 0 <= cy < 64:
                    c = cx + 64 * cy
                    K.b(P.SHAPE + c, rnd.choice([0x0f, 0x0f, 0x1f, 0x20, 0x42, 0, 0x2f, 0x35, 5, 0x11]))
                    K.b(P.OCC + c, rnd.choice([0, 0, 0, rnd.randint(1, 8)]))
        K.l(a7, (side << 16) | x); K.w(a7 + 4, y)
        return ['callcap 12a14 3000000 %s'], (lambda mm: P.swamp(mm, side, x, y)), dict(side=side, x=x, y=y)
    if routine == 'knight':
        rnd_gate(K, rnd, m, side, 'knight', 0x20)
        rnd_entities(K, rnd, m)
        K.w(0x3c4ca, rnd.randint(0, 0xfff)); K.w(0x3d526, rnd.randint(0, 0xfff))
        K.l(a7, side << 16)
        return ['callcap 12ba0 3000000 %s'], (lambda mm: P.knight(mm, side)), dict(side=side)
    if routine == 'arma':
        rnd_gate(K, rnd, m, side, 'arma', 0x100)
        rnd_entities(K, rnd, m)
        K.l(a7, side << 16)
        return ['callcap 12d26 3000000 %s'], (lambda mm: P.armageddon(mm, side)), dict(side=side)
    if routine == 'fe00':
        n = rnd_entities(K, rnd, m, 1, 60)
        if rnd.random() < 0.15:                     # no enemy at all
            for i in range(n):
                K.b(P.ent(i) + 1, 0)
        i = rnd.randint(0, n - 1)
        if rnd.random() < 0.4:                      # crowd everyone near the knight: ties
            c0 = P.rw(m, P.ent(i) + 8)
            for k in range(n):
                x = min(63, max(0, (c0 & 63) + rnd.randint(-3, 3))); y = min(63, max(0, (c0 >> 6) + rnd.randint(-3, 3)))
                K.w(P.ent(k) + 8, x + 64 * y)
        K.l(a7, P.ent(i))
        return ['callcap fe00 3000000 %s'], (lambda mm: P.knight_find_target(mm, P.ent(i))), dict(i=i, n=n)
    if routine == 'feca':
        n = rnd_entities(K, rnd, m, 2, 40)
        i, j = rnd.sample(range(n), 2)
        K.b(P.ent(i), 2)
        if rnd.random() < 0.5:
            K.l(P.ent(i) + 14, P.ent(rnd.randint(0, n - 1)))
        K.b(P.ent(j), rnd.choice([1, 2, 0x22, 0x42, 9]))
        K.w(P.ent(i) + 4, rnd.randint(1, 32000)); K.w(P.ent(j) + 4, rnd.randint(1, 32000))
        K.b(P.ent(i) + 3, rnd.randint(0, 20)); K.b(P.ent(j) + 3, rnd.randint(0, 20))
        K.w(P.ent(j) + 12, rnd.randint(0, 0x90))
        sd = P.rb(m, P.ent(i) + 1)
        K.w(P.SIDE + 16 * sd, rnd.choice([0, i + 1, j + 1, rnd.randint(1, n)]))
        K.w(P.QUERY, rnd.choice([0, i + 1, j + 1, rnd.randint(1, n)]))
        K.l(P.SIDE + 16 * sd + 8, rnd.randint(0, 50000))
        K.l(a7, (i << 16) | j)
        return ['callcap feca 3000000 %s'], (lambda mm: P.walker_merge(mm, i, j)), dict(i=i, j=j)
    if routine == 'raze':
        n = rnd_entities(K, rnd, m, 2, 40)
        wi, li = rnd.sample(range(n), 2)
        W, L = P.ent(wi), P.ent(li)
        ws = rnd.randint(0, 1)
        K.b(W + 1, ws); K.b(L + 1, 1 - ws)
        K.b(W, rnd.choice([8, 0x0a])); K.w(W + 4, rnd.randint(1, 3000)); K.w(W + 6, li)
        town = rnd.random() < 0.6
        K.l(W + 14, P.ent(li) if (town or rnd.random() < 0.5) else 0)
        K.b(W + 20, rnd.choice([0, 1, 2])); K.b(L + 20, rnd.choice([0, 0, 1]))
        K.w(W + 10, rnd.choice([0, 1, -64 & 0xffff]))
        lc = rnd.randint(130, 0xfff - 130)
        K.w(L + 8, lc); K.w(W + 8, lc)
        K.w(L + 10, rnd.choice([0, 1, 64]))
        K.w(L + 4, rnd.randint(-40, 0))
        K.l(L + 14, rnd.choice([0, 0, P.ent(wi)]))
        if town:
            K.b(L, 9)
            castle = rnd.random() < 0.3
            col = (1 - ws) + 0x1f
            for k in range(25):
                c = lc + P.rw(m, P.FOOT + 2 * k)
                K.b(P.SHAPE + c, rnd.choice([col, col, col, 0x0f, 0x2f, 0, ws + 0x1f]) if (k < 17 or castle) else rnd.choice([col, 0x0f]))
                K.b(P.FEAT + c, (rnd.choice([0x29, 0x2a, 0x2b, 0x2c, 0]) if 0 < k < 9 else 0) if castle else rnd.choice([0, 0, 0, 0x32]))
            K.b(P.FEAT + lc, 0x2a if castle else rnd.choice([0x20, 0x23, 0x29, 0x2a, 0]))
        else:
            K.b(L, rnd.choice([8, 0x0a]))
            K.w(L + 6, wi)
        K.b(P.OCC + lc, rnd.choice([0, li + 1, wi + 1]))
        K.w(P.SIDE + 16 * (1 - ws), rnd.choice([0, li + 1]))
        K.w(P.QUERY, rnd.choice([0, li + 1, wi + 1]))
        for s in (0, 1):
            K.l(P.mana_a(s), rnd.randint(-250, 5000))
        K.l(a7, (wi << 16) | li)
        return ['callcap 108b8 3000000 %s'], (lambda mm: P.combat_resolve(mm, wi, li)), dict(wi=wi, li=li, town=town)
    raise ValueError(routine)


PRE_FIELDS = [P.mana_a(0) + k for k in range(4)] + [P.mana_a(1) + k for k in range(4)] + \
             [P.SCORE + k for k in range(4)] + [b + k for b in P.BOX for k in (0, 1)] + \
             [P.SOUND, P.SOUND + 1] + [P.VIEWOFF + k for k in range(4)]


def run_snap(snap, routines, N, rnd, tot, fails, cov):
    regs = get_regs(os.path.join(WORK, snap))
    a7 = regs['A7']
    m = bytearray(ram(os.path.join(WORK, snap)))
    K = Poker(m)
    lines, cases = [], []
    for routine in routines:
        for k in range(N):
            cl, fn, info = make_case(K, rnd, m, routine, a7)
            if cl == 'eq':
                side, x, y = fn
                # (a) the pre-part, stopped by the loop detector in the first shake frame
                lines += K.flush()
                pre = bytes(m)
                ja = os.path.join(CCD, '%s_%d_a.json' % (snap[:-5], len(cases)))
                lines.append('callcap 12350 3000000 %s' % ja)
                cases.append(('eq_pre', pre, ja, (lambda mm, s=side, x=x, y=y: P.earthquake_pre(mm, s, x, y)), info))
                # (b) the post-part from the model's pre-state
                mm = bytearray(m)
                if not P.earthquake_pre(mm, side, x, y):
                    continue
                for a in range(LO, HI):
                    if mm[a] != m[a]:
                        K.b(a, mm[a])
                A6 = a7 + 0x40
                K.l(A6 + 4, SENT); K.w(A6 + 8, side); K.w(A6 + 10, x); K.w(A6 + 12, y)
                lines += K.flush()
                pre = bytes(m)
                jb = os.path.join(CCD, '%s_%d_b.json' % (snap[:-5], len(cases)))
                lines.append('callcap 12470 3000000 %s A6=%x PC=12470' % (jb, A6))
                cases.append(('eq_post', pre, jb, (lambda mm, s=side, x=x, y=y: P.earthquake_post(mm, s, x, y)), info))
                continue
            lines += K.flush()
            pre = bytes(m)
            j = os.path.join(CCD, '%s_%d.json' % (snap[:-5], len(cases)))
            lines.append(cl[0] % j)
            cases.append((routine, pre, j, fn, info))
    out = repl_batch(os.path.join(WORK, snap), lines)
    for routine, pre, j, fn, info in cases:
        oc, mem, d = load_cc(j)
        real = real_delta(pre, mem, a7)
        mm = bytearray(pre)
        try:
            res = fn(mm)
            model = region_delta(pre, mm, a7)
        except AssertionError as ex:
            res, model = None, {'assert': str(ex)}
        if routine == 'eq_pre':
            if res:
                # stopped in shake frame 1 or 2: $2287a is pre-$a0-$1e0 or pre-$a0
                vos = {((P.rl(pre, P.VIEWOFF) - d) & 0xffffffff).to_bytes(4, 'big') for d in (0x280, 0xa0)}
                fields = [a for a in PRE_FIELDS if not P.VIEWOFF <= a < P.VIEWOFF + 4]
                good = ('Loop detected at PC=$00016f10' in oc and all(real.get(a, pre[a]) == mm[a] for a in fields)
                        and bytes(real.get(P.VIEWOFF + k, pre[P.VIEWOFF + k]) for k in range(4)) in vos)
            else:
                good = oc == 'returned' and model == real
        else:
            good = oc == 'returned' and model == real
        key = routine
        t = tot.setdefault(key, [0, 0]); t[0 if good else 1] += 1
        tag = 'changed' if model else 'refused'
        cov.setdefault(key, {}).setdefault(tag, 0); cov[key][tag] += 1
        if not good and len(fails) < 20:
            dm = {hex(a): (pre[a], real.get(a), mm[a]) for a in sorted(set(real) | set(model if isinstance(model, dict) else {}))
                  if real.get(a, pre[a]) != mm[a]} if 'assert' not in model else model
            fails.append((routine, snap, info, oc, list(dm.items())[:12], len(dm)))


def main():
    N = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    rnd = random.Random(int(sys.argv[2]) if len(sys.argv) > 2 else 1)
    filt = sys.argv[3].split(',') if len(sys.argv) > 3 else ['flood', 'eq', 'volcano', 'swamp', 'knight', 'arma', 'fe00', 'feca', 'raze']
    os.makedirs(CCD, exist_ok=True)
    sys.setrecursionlimit(100000)
    tot, fails, cov = {}, [], {}
    for snap in SNAPS:
        run_snap(snap, filt, N, rnd, tot, fails, cov)
    for k, (g, b) in sorted(tot.items()):
        print('%-8s %4d / %4d   %s' % (k, g, g + b, cov.get(k)))
    print('paths', sorted(P.COV.items()))
    for f in fails:
        print('FAIL', f)


if __name__ == '__main__':
    main()
