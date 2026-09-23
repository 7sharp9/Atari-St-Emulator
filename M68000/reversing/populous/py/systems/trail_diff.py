"""trail_diff.py - callcap differential test of trail_ref.py against $12f84 and $13372.

  python trail_diff.py [N_per_routine] [seed]

Base state: systems/spawn.snap. Each case pokes a randomized state (w lines), runs
`callcap <routine>` on the real code and compares the full memory delta in $ad58..$3d550 (program
+ DATA + BSS; the stack and the screens are outside it) with the model applied to the same state.
$12f84 cases: both trail slots with random str/type/anim/frame bounds/direction/cell (edges
biased), random terrain classes and features around each slot, and walker victims (some fighting,
some the query entity) on the marked cells. $13372 cases: random type (incl. 3 and -1), edge 0..3,
slot occupancy, seed, human side, key pass/fail, and the uninitialised local at -14(A6).
"""
import os, random, re, struct, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from popcfg_local import OUT, R, DLL, DISK
import trail_ref as T
from popmem import ram

LO, HI = 0xad58, 0x3d550
SNAP = os.path.join(OUT, 'spawn.snap')


class Poker:
    def __init__(self, m): self.m = m; self.dirty = set()
    def b(self, a, v): self.m[a] = v & 0xff; self.dirty.add(a & ~3)
    def w(self, a, v): self.b(a, v >> 8); self.b(a + 1, v)
    def l(self, a, v): self.w(a, v >> 16); self.w(a + 2, v)
    def flush(self):
        out = ['w %x %08x' % (a, struct.unpack_from('>I', self.m, a)[0]) for a in sorted(self.dirty)]
        self.dirty = set(); return out


CLASSES = [0, 0x0f, 0x0f, 0x10, 0x1f, 0x20, 0x2f, 0x30, 0x35, 0x42, 0x05, 0x11, 0x1a]
DIRS = [0, 1, -1, 64, -64, 65, -65]


def rand_tick(P, rnd, m):
    leaders = {T.rw(m, T.SIDE) - 1, T.rw(m, T.SIDE + 16) - 1}
    used = set()
    for slot in (0xd1, 0xd2):
        e = T.ENT + slot * T.ESZ
        typ = rnd.randint(0, 2)
        P.w(e + 4, rnd.choice([0, 1, 1, 1, 7]))
        P.b(e + 20, typ)
        P.w(e + 12, rnd.choice([7, 7, 7, 8, 0, 3, 6]))
        P.b(e + 2, rnd.choice([T.tbl(m, typ, 2), rnd.randint(0, 15)]))
        P.b(e + 3, rnd.choice([T.tbl(m, typ, 1), rnd.randint(0, 15)]))
        P.w(e + 6, rnd.randint(0, 15))
        P.b(e + 21, rnd.choice([1, 0xff]))
        P.w(e + 10, rnd.choice([0, T.tbl(m, typ, 0), T.tbl(m, typ, 0), rnd.choice(DIRS)]))
        if rnd.random() < 0.25:
            x = rnd.choice([0, 1, 62, 63, rnd.randint(0, 63)]); y = rnd.choice([0, 1, 62, 63, rnd.randint(0, 63)])
        else:
            x, y = rnd.randint(0, 63), rnd.randint(0, 63)
        cell = y * 64 + x
        P.w(e + 8, cell)
        P.b(T.OCC + cell, rnd.choice([slot + 1, slot + 1, 0, 5]))
        nxt = cell + T.s16(T.rw(m, e + 10) or T.tbl(m, typ, 0))
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                c = nxt + dy * 64 + dx
                if 0 <= c < 4096 and c != cell:
                    P.b(T.CLASS + c, rnd.choice(CLASSES))
                    P.b(T.FEAT + c, rnd.choice([0, 0, 0x32, 0x21, 0x2a]))
                    P.b(T.OCC + c, 0)
        # victims on the marked cells
        for k in range(3):
            c = nxt + T.tbl(m, typ, 3 + k)
            if not (0 <= c < 4096) or rnd.random() < 0.5:
                continue
            idx = rnd.choice([i for i in range(40, 0xd0) if i not in leaders and i not in used])
            used.add(idx)
            v = T.ENT + idx * T.ESZ
            fl = rnd.choice([2, 2, 8, 0x12, 4])
            P.b(v, fl); P.b(v + 1, rnd.randint(0, 1)); P.w(v + 4, rnd.randint(1, 600))
            P.w(v + 8, c); P.w(v + 10, rnd.choice(DIRS))
            if fl == 8:
                opp = rnd.choice([i for i in range(40, 0xd0) if i not in used])
                used.add(opp)
                P.w(v + 6, opp); P.b(T.ENT + opp * T.ESZ, 9)
            P.b(T.OCC + c, idx + 1)
            c2 = c - T.s16(T.rw(m, v + 10))
            if 0 <= c2 < 4096 and rnd.random() < 0.5:
                P.b(T.OCC + c2, idx + 1)
            if rnd.random() < 0.2:
                P.w(0x3c4c6, idx + 1)
    # settlements and leaders on a marked cell take paths the model does not cover
    # ($10366 land release, $129d6): take them off the occupancy map
    for slot in (0xd1, 0xd2):
        e = T.ENT + slot * T.ESZ
        typ = T.s8(m[e + 20])
        nxt = T.rsw(m, e + 8) + T.s16(T.rw(m, e + 10) or T.tbl(m, typ, 0))
        for k in range(3):
            c = nxt + T.tbl(m, typ, 3 + k)
            if 0 <= c < 4096 and m[T.OCC + c] and m[T.OCC + c] - 1 < 0xd1:
                j = m[T.OCC + c] - 1
                if m[T.ENT + j * T.ESZ] & 1 or j in leaders:
                    P.b(T.OCC + c, 0)


def rand_spawn(P, rnd, m, a7):
    for slot in (0xd1, 0xd2):
        e = T.ENT + slot * T.ESZ
        P.w(e + 4, rnd.choice([0, 0, 1, 0xffff, 3]))
        P.w(e + 8, rnd.randint(0, 4095)); P.w(e + 12, rnd.randint(0, 9))
    P.w(T.SEED, rnd.randint(0, 0x7fff))
    P.w(0x3affe, rnd.randint(0, 1))
    good = (T.rl(m, T.KEY_58) + 0x12312378) & 0xffffffff
    P.l(T.KEY_B4, good if rnd.random() < 0.6 else rnd.getrandbits(32))
    P.w(T.FRAME, rnd.randint(0, 0x2000))
    P.l(a7 - 22, rnd.choice([0x3d400, 0x3d480, 0x3c000]) + 2 * rnd.randint(0, 30))   # -14(A6)
    typ = rnd.choice([0, 1, 2, 2, 3, 0xffff])
    edge = rnd.choice([0, 1, 2, 3, 0x1234])
    P.l(a7, (typ << 16) | edge)
    return typ, edge


def main():
    N = int(sys.argv[1]) if len(sys.argv) > 1 else 200
    rnd = random.Random(int(sys.argv[2]) if len(sys.argv) > 2 else 4242)
    env = dict(os.environ, ATARI_NOTRACE='1')
    out = subprocess.run(['dotnet', 'exec', DLL, 'resume', SNAP, 'repl', '--disk-a', DISK], input='r\nq\n',
                         capture_output=True, text=True, cwd=R, env=env).stdout
    a7 = int(re.search(r'A7:([0-9a-f]{8})', out).group(1), 16)
    m = bytearray(ram(SNAP))
    P = Poker(m)
    lines, cases = [], []
    for routine in (0x12f84, 0x13372):
        for i in range(N):
            args = ()
            if routine == 0x12f84:
                rand_tick(P, rnd, m)
            else:
                args = rand_spawn(P, rnd, m, a7)
            lines += P.flush()
            cases.append((routine, args, bytes(m)))
            lines.append('callcap %x 400000 -' % routine)
    p = subprocess.run(['dotnet', 'exec', DLL, 'resume', SNAP, 'repl', '--disk-a', DISK],
                       input='\n'.join(lines + ['q']) + '\n', capture_output=True, text=True, cwd=R, env=env)
    blocks = re.split(r'--- callcap \$', p.stdout)[1:]
    assert len(blocks) == len(cases), (len(blocks), len(cases), p.stdout[-1500:])
    tot, cov, fails = {}, {}, []
    for (routine, args, pre), blk in zip(cases, blocks):
        real = {}
        for a, x0, x1 in re.findall(r'mem \$([0-9a-f]{6}) \$([0-9a-f]{2})->\$([0-9a-f]{2})', blk):
            a = int(a, 16)
            if LO <= a < HI:
                real[a] = int(x1, 16)
        ok_run = 'returned' in blk.split('\n')[0]
        mm = bytearray(pre)
        note = ''
        try:
            if routine == 0x12f84:
                T.tick_12f84(mm)
            else:
                s = T.spawn_13372(mm, args[0], args[1], a7 - 8)
                note = 'none' if s is None else 'slot%x' % s
                if s is not None and T.rw(mm, T.FRAME) != T.rw(pre, T.FRAME): note += '/penalty'
        except T.NotModelled as ex:
            note = 'NM ' + str(ex)
        model = {a: mm[a] for a in range(LO, HI) if mm[a] != pre[a]}
        good = ok_run and model == real and not note.startswith('NM')
        if routine == 0x12f84:
            steps = sum(1 for s in (0xd1, 0xd2) if T.rw(pre, T.ENT + s * T.ESZ + 4) and T.s16(T.rw(pre, T.ENT + s * T.ESZ + 12)) >= 7)
            died = sum(1 for s in (0xd1, 0xd2) if T.rw(pre, T.ENT + s * T.ESZ + 4) and not T.rw(mm, T.ENT + s * T.ESZ + 4))
            kills = sum(1 for j in range(0xd1) if T.rw(pre, T.ENT + j * T.ESZ + 4) and not T.rw(mm, T.ENT + j * T.ESZ + 4))
            marks = sum(1 for c in range(4096) if pre[T.CLASS + c] != mm[T.CLASS + c] or pre[T.FEAT + c] != mm[T.FEAT + c])
            note = note or 'steps%d' % steps
            for key, v in (('steps', steps), ('died', died), ('kills', kills), ('marked', marks)):
                cov.setdefault(routine, {}).setdefault(key, 0); cov[routine][key] += v
        else:
            cov.setdefault(routine, {}).setdefault(note, 0); cov[routine][note] += 1
        t = tot.setdefault(routine, [0, 0]); t[0 if good else 1] += 1
        if not good and len(fails) < 12:
            fails.append((hex(routine), args, note, ok_run,
                          sorted(set(real) ^ set(model))[:8],
                          [(hex(a), real.get(a), model.get(a)) for a in sorted(set(real) | set(model))
                           if real.get(a) != model.get(a)][:8]))
    for routine, (g, b) in sorted(tot.items()):
        print('TOTAL %06x  %d/%d' % (routine, g, g + b))
    for routine, d in sorted(cov.items()):
        print('coverage %06x' % routine, ' '.join('%s:%d' % kv for kv in sorted(d.items())))
    for f in fails:
        print('FAIL', f)


if __name__ == '__main__':
    main()
