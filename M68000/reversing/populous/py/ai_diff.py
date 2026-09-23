"""ai_diff.py - differential test: ai_ref.py reconstructions vs the real 68000 routines via callcap.

For each base snapshot, generate N randomized input states (pokes of the fields each routine
reads), run `callcap <routine>` on the real code in one REPL session, and compare the full
persistent memory delta (everything except the stack scratch below the entry SP) and, for $135fc,
the returned D0 low byte, against the Python model applied to the same state.

usage: python ai_diff.py [N_per_routine_per_snap] [seed]
"""
import os, random, re, struct, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ai_ref as A
import hx

from popcfg import R, WORK
S = WORK + '/'
SNAPS = ['game_start.snap', 'g40.snap', 'g90.snap']


def repl(snap, lines):
    env = dict(os.environ, ATARI_NOTRACE='1')
    p = subprocess.run(['dotnet', 'exec', 'bin/Debug/net8.0/M68000.dll', 'resume', S + snap, 'repl',
                        '--disk-a', S + 'pop_auto.st'], input='\n'.join(lines + ['q']) + '\n',
                       capture_output=True, text=True, cwd=R, env=env)
    return p.stdout + p.stderr


def get_a7(snap):
    out = repl(snap, ['r'])
    return (int(re.search(r'A7:([0-9a-f]{8})', out).group(1), 16),
            int(re.search(r'D0:([0-9a-f]{8})', out).group(1), 16))


class Poker:
    """tracks the session RAM image and emits `w` lines for changed 4-byte blocks."""
    def __init__(self, m): self.m = m; self.dirty = set()
    def b(self, a, v): self.m[a] = v & 0xff; self.dirty.add(a & ~3)
    def w(self, a, v): self.b(a, v >> 8); self.b(a + 1, v)
    def l(self, a, v): self.w(a, v >> 16); self.w(a + 2, v)
    def flush(self):
        out = ['w %x %08x' % (a, struct.unpack_from('>I', self.m, a)[0]) for a in sorted(self.dirty)]
        self.dirty = set(); return out


def walker_ptrs(m):
    n = max(1, A.rw(m, 0x3c4e2))
    return [A.WALK + i * A.WSZ for i in range(n)]


def randomize_common(P, rnd, m, side):
    """fields read by $13eda/$13a44/$13dce."""
    ws = walker_ptrs(m)
    n = len(ws)
    for s in (0, 1):
        r, st = A.rec(s), A.sidest(s)
        P.w(r + 8, 0)                                    # not busy (caller's gate)
        P.w(r + 12, rnd.randint(1, 10))                  # rating / 10-aggression
        P.w(r + 14, rnd.getrandbits(9))                  # options mask
        P.w(r + 18, rnd.randint(0, 8))                   # power counter
        P.w(r + 20, rnd.choice([0, 1, 3, 10, 20]))       # castles
        P.w(r + 22, rnd.choice([0, 2, 5, 12, 30, 40]))   # houses
        P.w(r + 26, rnd.randint(0, 2))
        P.w(r + 24, A.rw(m, r + 26) + 1 + rnd.randint(0, 4))
        P.w(r + 28, rnd.choice([0, 0, 1, 2]))
        for f in (34, 38, 42):
            P.l(r + f, rnd.choice(ws + ([0] if f == 38 else [])))
        P.w(st + 0, rnd.choice([0] + list(range(1, n + 1))))              # leader idx+1
        P.w(st + 4, rnd.choice([0, 0, 1, 2, 3]))                          # mode
        P.l(st + 8, rnd.randint(0, 6000))                                  # population
        P.l(st + 12, rnd.choice([rnd.randint(0, 3000), rnd.randint(2900, 11000),
                                  rnd.randint(40000, 82000), 3000, 3001, 5500, 5501, 8000, 8001,
                                  10500, 10501, 41999, 42000, 80999, 81000]))
    for wp in ws:
        P.w(wp + 4, rnd.choice([rnd.randint(1, 9000), 3000, 3001, 6000, 5999]))
        P.w(wp + 8, rnd.randint(0, 0xfff))
        P.b(wp + 0, rnd.choice([1, 2, 0x12]))
        P.b(wp + 1, rnd.randint(0, 1))
    # make magnets/targets collide sometimes
    for s in (0, 1):
        r, st = A.rec(s), A.sidest(s)
        pick = rnd.random()
        if pick < 0.25:
            P.w(st + 2, A.rw(m, A.rl(m, r + 42) + 8))
        elif pick < 0.5:
            P.w(st + 2, A.rw(m, A.rl(m, r + 34) + 8))
        elif pick < 0.6:
            P.w(st + 2, A.rw(m, r + 30))
        else:
            P.w(st + 2, rnd.randint(0, 0xfff))
        if rnd.random() < 0.3:
            P.w(r + 30, A.rw(m, A.leader_ptr(m, s) + 8) if A.leader_ptr(m, s) else 0)
        else:
            P.w(r + 30, rnd.randint(0, 0xfff))
        mg = A.rw(m, st + 2)
        P.b(A.OCC + mg, rnd.choice([0, 0, rnd.randint(1, len(ws))]))
    if rnd.random() < 0.3:
        P.w(A.sidest(1) + 2, A.rw(m, A.sidest(0) + 2))
    P.w(A.FRAME, rnd.randint(0, 0xffff))
    P.w(A.SEED, rnd.randint(0, 0x7fff))


def randomize_land(P, rnd, m, side, routine):
    cell = rnd.randint(0, 0xfff)
    x0, y0 = cell & 0x3f, cell >> 6
    r, st = A.rec(side), A.sidest(side)
    P.w(r + 8, rnd.choice([0, 0, 0, 1]))
    P.w(r + 14, rnd.getrandbits(9) | (1 if rnd.random() < 0.85 else 0))
    P.w(A.FLAGS, rnd.choice([0, 0, 0, 4, 8, 0x10, 0x18, 1, 2]))
    P.l(st + 12, rnd.choice([0, 19, 20, 500]))
    P.w(st + 6, rnd.choice([0, 10, 50, 51]))
    base = rnd.randint(0, 6)
    rad = 4 if routine == 0x135fc else 1
    flat = rnd.random() < 0.4
    for dy in range(-rad, rad + 2):
        for dx in range(-rad, rad + 2):
            px, py = x0 + dx, y0 + dy
            if 0 <= px <= 64 and 0 <= py <= 64:
                h = base if (flat and rnd.random() < 0.9) else max(0, base + rnd.randint(-2, 2))
                P.w(A.HGT + (px + py * 65) * 2, h)
                if px < 64 and py < 64:
                    P.b(A.OBJ + px + py * 64, rnd.choice([0, 0, 0, 0x0f, 0x2f, 0x30, 0x35, 0x42, 0x10]))
    return cell


def main():
    N = int(sys.argv[1]) if len(sys.argv) > 1 else 50
    rnd = random.Random(int(sys.argv[2]) if len(sys.argv) > 2 else 1234)
    tot = {}
    cov = {}
    fails = []
    for snap in SNAPS:
        a7, d0pre = get_a7(snap)
        m = bytearray(hx.load(S + snap))
        P = Poker(m)
        lines, cases = [], []
        for routine in (0x13eda, 0x13a44, 0x135fc, 0x13816):
            for i in range(N):
                side = rnd.randint(0, 1)
                if routine in (0x13eda, 0x13a44):
                    randomize_common(P, rnd, m, side)
                    P.l(a7, side << 16)
                    args = (side,)
                else:
                    cell = randomize_land(P, rnd, m, side, routine)
                    P.l(a7, (cell << 16) | side)
                    args = (cell, side)
                lines += P.flush()
                pre = bytes(m)
                lines.append('callcap %x 200000 -' % routine)
                cases.append((routine, args, pre))
        out = repl(snap, lines)
        # parse callcap blocks
        blocks = re.split(r'--- callcap \$', out)[1:]
        assert len(blocks) == len(cases), (snap, len(blocks), len(cases), out[-2000:])
        for (routine, args, pre), blk in zip(cases, blocks):
            real = {}
            for a, x0, x1 in re.findall(r'mem \$([0-9a-f]{6}) \$([0-9a-f]{2})->\$([0-9a-f]{2})', blk):
                a = int(a, 16)
                if a7 - 0x400 <= a < a7 + 4: continue          # stack scratch / args
                real[a] = int(x1, 16)
            ok_run = 'returned' in blk.split('\n')[0]
            d0m = re.search(r'D0 \$[0-9a-f]{8}->\$([0-9a-f]{8})', blk)
            mm = bytearray(pre)
            fn = {0x13eda: A.think_13eda, 0x13a44: A.powers_13a44,
                  0x135fc: A.flatten_135fc, 0x13816: A.level_13816}[routine]
            ret = fn(mm, *args)
            model = {a: mm[a] for a in range(len(mm)) if mm[a] != pre[a]}
            good = ok_run and model == real
            if routine == 0x135fc:
                rd0 = (int(d0m.group(1), 16) if d0m else d0pre) & 0xff
                good = good and rd0 == ret
            side = args[-1]
            rr = A.rec(side)
            if mm[rr] != pre[rr] or mm[rr + 1] != pre[rr + 1] or mm[rr + 2] != pre[rr + 2] or model:
                oc = 'cmd%d/%d' % (mm[rr], mm[rr + 2]) if mm[rr] == 0xe else 'cmd%d' % mm[rr]
                if not model: oc = 'none'
            else:
                oc = 'none'
            if routine == 0x135fc: oc += '/ret%d' % ret
            cov.setdefault(routine, {}).setdefault(oc, 0); cov[routine][oc] += 1
            key = (routine, snap)
            t = tot.setdefault(key, [0, 0]); t[0 if good else 1] += 1
            if not good and len(fails) < 30:
                fails.append((hex(routine), snap, args, {hex(k): v for k, v in real.items()},
                              {hex(k): v for k, v in model.items()}, ret, blk.split('\n')[0]))
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
