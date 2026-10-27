"""Gate for sabotage (the PLANT EXPLOSIVES screen `$3f98`): the charges `$4516`, a click on a building `$404e`, the
blast `$41f6..$4272` (with `$4340`/`$5816`), the charge cleared after the explosion `$429e..$42c4`, the cancel `$482e`,
and the supply update `$f56e`/`$f5e2` after a blast, run by the game in `stserver` and checked against
sabotage_model.py and army_model.supply call by call.

usage: gate_sabotage.py [control]
Needs the driven snapshots made by drive_sabotage.sh in $SABOTAGE_WORK (default <root>/scratchpad/midwinter/
sabotage) and <root>/scratchpad/midwinter/zuul067.st. Legs:
- natural: the REPL clicks of the three driven sabotages (village node 74: Church and House; held node 48: the
  Warehouse; held node 88: the Headquarters): the toggles (s4_sab -> s5_planted, p48_sab -> p48_planted,
  p88_sab -> p88_planted, from the snapshots alone), each blast and its clear from the plunger click (n*_41f6), the
  cancel from the back icon (n73_482e);
- poked (labelled pokes on s4_sab.snap): the charges for 400 performance words; 1500 clicks on random sites, cells,
  marks, explosives straddling the charge, clocks; 1700 blasts covering every building type at held and free sites,
  guarded and not, both stations of every cable-car pair, Morale below, at and over the cap, counts at $ff; 300
  cancels; and the supply update before and after blowing up each Warehouse, Synthesis Plant and Factory of the
  list at held and free sites.
A control name runs a broken model, which must fail: nocable, keepguard, noheldbonus, nocap, chargele (a charge left
when the explosives reach exactly 0 counts as short), plus0 (charges without the +1), cancelclock (no minutes
refunded), ruinsupplies (supply computed as if the Ruin were still a Warehouse or Synthesis Plant).
"""
import os, random, sys

HERE = os.path.dirname(os.path.abspath(__file__))
root = os.environ.get('M68000_ROOT') or HERE
while not os.path.exists(os.path.join(root, 'tools', 'rdis.py')):
    root = os.path.dirname(root)
WORK = os.environ.get('SABOTAGE_WORK') or os.path.join(root, 'scratchpad', 'midwinter', 'sabotage')
DISK = os.path.join(root, 'scratchpad', 'midwinter', 'zuul067.st')
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(root, 'reversing', 'midwinter', 'py', 'army'))
sys.path.insert(0, os.path.join(root, 'tools'))
import sabotage_model as sm  # noqa: E402
import army_model as am  # noqa: E402
from army_model import Mem  # noqa: E402
from stclient import StServer  # noqa: E402
from disassemble import ram_from_snap  # noqa: E402

FEAT_END = 0x2b16a
OUTREG = [(sm.FEAT, FEAT_END - sm.FEAT), (sm.PLANTED, 10), (sm.CHARGES, 34), (sm.MORALE, 2), (sm.DESTROYED, 20),
          (sm.HQ_GONE, 2)]
UNITS = (0x2bb96, 512)
NODESTATE = (0x2bb36, 96)
STARK = 14
SNAP = lambda n: os.path.join(WORK, n + '.snap')  # noqa: E731
CTL = sys.argv[1] if len(sys.argv) > 1 else None


def broken():
    if CTL == 'nocable':
        real = sm.blast_one

        def f(m):
            s = sm.site(m)
            a = s
            while not m.u8(a + 6) & 0x40:
                a += 2
            if m.u8(a + 6) & 0x1f == sm.CABLE:
                save = {x: m.u8(x) for x in (a - 2, a + 14)}
                r = real(m)
                for x, v in save.items():
                    m.set8(x, v)
                return r
            return real(m)
        sm.blast_one = f
    elif CTL == 'keepguard':
        real = sm.blast_one

        def f(m):
            s = sm.site(m)
            a = s
            while not m.u8(a + 6) & 0x40:
                a += 2
            g = m.u8(a + 6) & 0x80
            r = real(m)
            m.set8(r, m.u8(r) | g)
            return r
        sm.blast_one = f
    elif CTL == 'noheldbonus':
        def g(m, kind, t):
            d = 5 + (5 if t in sm.SUPPLYISH else 0)
            m.setw(sm.MORALE, min((m.w(sm.MORALE) + d) & 0xffff, (m.u8(sm.rec(m) + 6) + 500) // 3))
        sm.morale_gain = g
    elif CTL == 'nocap':
        def g(m, kind, t):
            d = 5 + (5 if kind & 0x80 else 0) + (5 if t in sm.SUPPLYISH else 0)
            m.setw(sm.MORALE, (m.w(sm.MORALE) + d) & 0xffff)
        sm.morale_gain = g
    elif CTL == 'chargele':
        real = sm.toggle

        def f(m, i):
            if i < m.w(sm.COUNT):
                b = sm.site(m) + 6 + 2 * i
                t2 = 2 * (m.u8(b) & 0x1f)
                if not m.u8(b) & 0x40 and m.w(sm.EXPL) == m.w(sm.CHARGES + t2):
                    return  # planted and taken back: nothing changes
            real(m, i)
        sm.toggle = f
    elif CTL == 'plus0':
        def f(m):
            d = (m.w(sm.PERF) + 70) & 0xffff
            for t in range(17):
                m.setw(sm.CHARGES + 2 * t, m.w(sm.WEIGHT + 2 * t) // d if d else m.w(sm.WEIGHT + 2 * t))
        sm.charges = f
    elif CTL == 'cancelclock':
        def f(m):
            s = sm.site(m)
            for j in range(m.u8(s) & 0x7f):
                b = s + 6 + 2 * j
                if m.u8(b) & 0x40:
                    m.set8(b, m.u8(b) & ~0x40)
                    m.setw(sm.EXPL, m.w(sm.EXPL) + m.w(sm.CHARGES + 2 * (m.u8(b) & 0x1f)))
        sm.cancel = f
    elif CTL not in (None, 'ruinsupplies'):
        sys.exit(f'unknown control {CTL}')


class Score:
    def __init__(self):
        self.n, self.ok, self.shown = {}, {}, 0

    def add(self, label, good, why=''):
        self.n[label] = self.n.get(label, 0) + 1
        self.ok[label] = self.ok.get(label, 0) + bool(good)
        if not good and self.shown < 8:
            self.shown += 1
            print(f'  {label} differs: {why}')

    def regions(self, label, m, got_read, regions=OUTREG):
        diffs = []
        for a, ln in regions:
            got, exp = got_read(a, ln), bytes(m.b[a:a + ln])
            diffs += [(hex(a + j), exp[j], got[j]) for j in range(ln) if exp[j] != got[j]]
        self.add(label, not diffs, diffs[:6])


def records(m):
    out, a = [], sm.FEAT
    while m.u8(a):
        out.append(a)
        a += 6 + 2 * (m.u8(a) & 0x7f)
    return out


def main():
    broken()
    sc = Score()
    # ---- natural toggles, from the driven snapshots alone
    for before, after, cells in (('s4_sab', 's5_planted', [1, 2]), ('p48_sab', 'p48_planted', [0]),
                                 ('p88_sab', 'p88_planted', [0])):
        m, got = Mem(ram_from_snap(SNAP(before))), ram_from_snap(SNAP(after))
        for i in cells:
            sm.toggle(m, i)
        sc.regions('natural toggle', m, lambda a, n: got[a:a + n],
                   [(sm.FEAT, FEAT_END - sm.FEAT), (sm.PLANTED, 6)])
    s = StServer(root)
    # ---- natural blasts: from the plunger click to each building's blast and clear
    for name, n in (('n73_41f6', 2), ('n48_41f6', 1), ('n88_41f6', 1)):
        s('load', snapshot=SNAP(name), disk=DISK)
        for k in range(n):
            if k:
                r = s('run', max_steps=20000000, until_pc=0x41f6)
                assert r['reason'] == 'until', r
            m = Mem(s.read(0, 0x30000))
            units0 = s.read(*UNITS) + s.read(*NODESTATE)
            sm.blast_one(m)
            r = s('run', max_steps=2000000, until_pc=0x4272)
            assert r['reason'] == 'until', r
            sc.regions('natural blast', m, s.read)
            r = s('run', max_steps=20000000, until_pc=0x42c4)
            assert r['reason'] == 'until', r
            sm.clear_one(m)
            sc.regions('natural clear', m, s.read)
            sc.add('natural: units and node states untouched', units0 == s.read(*UNITS) + s.read(*NODESTATE))
    s('load', snapshot=SNAP('n73_482e'), disk=DISK)
    m = Mem(s.read(0, 0x30000))
    sm.cancel(m)
    r = s('run', max_steps=2000000, until_pc=0x310c)
    assert r['reason'] == 'until', r
    sc.regions('natural cancel', m, s.read)
    # ---- poked legs from the sabotage screen at the village
    s('load', snapshot=SNAP('s4_sab'), disk=DISK)
    base = s.read(0, 0x30000)
    fork = s('fork')['id']
    rng = random.Random(1989)
    m0 = Mem(base)
    recs = records(m0)
    by_type = {}
    for a in recs:
        for j in range(m0.u8(a) & 0x7f):
            by_type.setdefault(m0.u8(a + 6 + 2 * j) & 0x1f, []).append((a, j))
    stark = sm.RECS + 0x4a * STARK

    class St:
        def __init__(self):
            s('restore', id=fork)
            self.m = Mem(base)

        def poke(self, a, width, v):
            v &= (1 << 8 * width) - 1
            s('poke', addr=a, width=width, value=v)
            self.m.b[a:a + width] = v.to_bytes(width, 'big')

    # charges
    perfs = list(range(0, 260)) + [330, 331, 430, 431, 0xff00, 0xffb9, 0xffba, 0xffbb, 0xfffe, 0xffff] + \
        [rng.randrange(0x10000) for _ in range(130)]
    for p in perfs:
        st = St()
        st.poke(sm.PERF, 2, p)
        sm.charges(st.m)
        s.call(0x4516)
        sc.regions('charges $4516', st.m, s.read, [(sm.CHARGES, 34)])
    # clicks on a building cell
    for k in range(1500):
        st = St()
        multi = [r for r in recs if 2 <= m0.u8(r) & 0x7f <= 10]
        a = rng.choice(multi if rng.random() < 0.7 else [r for r in recs if m0.u8(r) & 0x7f == 1])
        n = st.m.u8(a) & 0x7f
        st.poke(stark + 52, 4, a)
        st.poke(sm.COUNT, 2, st.m.u8(a) & 0xf)
        for j in range(n):
            if rng.random() < 0.3:
                st.poke(a + 6 + 2 * j, 1, st.m.u8(a + 6 + 2 * j) | 0x40)
        st.poke(sm.PERF, 2, rng.choice([0, 61, 100, 250, rng.randrange(300)]))
        sm.charges(st.m)
        s.call(0x4516)
        i = rng.randrange(n) if rng.random() < 0.85 else rng.randrange(11)
        t = st.m.u8(a + 6 + 2 * min(i, n - 1)) & 0x1f
        c = st.m.w(sm.CHARGES + 2 * t)
        st.poke(sm.EXPL, 2, rng.choice([0, c - 1, c, c, c + 1, 47, rng.randrange(60)]))
        st.poke(sm.CLOCK, 2, rng.choice([360, 470, rng.randrange(0x7080)]))
        st.poke(sm.PLANTED, 2, rng.randrange(6))
        sm.toggle(st.m, i)
        s.call(0x404e, stops=[0x3fb2, 0x4002], d0=i)
        sc.regions('click $404e', st.m, s.read)
    # blasts
    types = sorted(by_type) + [sm.RUIN]
    every = [x for v in by_type.values() for x in v]
    for k in range(1700):
        st = St()
        t = types[k % len(types)]
        a, j = rng.choice(by_type[t] if t != sm.RUIN else every)
        n = st.m.u8(a) & 0x7f
        if t == sm.RUIN:                                   # a building already blown up
            st.poke(a + 6 + 2 * j, 1, (st.m.u8(a + 6 + 2 * j) & 0xe0) | sm.RUIN)
        st.poke(stark + 52, 4, a)
        if rng.random() < 0.5:
            st.poke(a, 1, st.m.u8(a) ^ 0x80)              # held <-> free
        b = a + 6 + 2 * j
        if rng.random() < 0.3:
            st.poke(b, 1, st.m.u8(b) ^ 0x80)              # guarded <-> not
        st.poke(b, 1, st.m.u8(b) | 0x40)
        for jj in range(j + 1, n):                         # later charges wait their turn
            if rng.random() < 0.3:
                st.poke(a + 6 + 2 * jj, 1, st.m.u8(a + 6 + 2 * jj) | 0x40)
        opt = rng.randrange(256)
        st.poke(stark + 6, 1, opt)
        cap = (opt + 500) // 3
        st.poke(sm.MORALE, 2, rng.choice([0, cap - 16, cap - 10, cap - 5, cap - 4, cap, cap + 3, rng.randrange(260)]))
        st.poke(sm.DESTROYED + t, 1, rng.choice([0, 1, 0xff, rng.randrange(256)]))
        st.poke(sm.HQ_GONE, 2, 0)
        units0 = s.read(*UNITS) + s.read(*NODESTATE)
        kinds0 = [st.m.u8(r) for r in recs]
        sm.blast_one(st.m)
        s.call(0x41f6, stops=[0x4272])
        sc.regions(f'blast $41f6 type {t:x}', st.m, s.read)
        sc.add('poked: units and node states untouched', units0 == s.read(*UNITS) + s.read(*NODESTATE))
        fl = s.read(sm.FEAT, FEAT_END - sm.FEAT)
        sc.add('poked: no kind byte (held bit) changed', kinds0 == [fl[r - sm.FEAT] for r in recs])
        sm.clear_one(st.m)
        s.call(0x429e, stops=[0x42c4])
        sc.regions('clear $429e', st.m, s.read)
    # cancel
    for k in range(300):
        st = St()
        a = rng.choice([r for r in recs if 1 <= m0.u8(r) & 0x7f <= 10])
        st.poke(stark + 52, 4, a)
        for j in range(st.m.u8(a) & 0x7f):
            if rng.random() < 0.5:
                st.poke(a + 6 + 2 * j, 1, st.m.u8(a + 6 + 2 * j) | 0x40)
        st.poke(sm.EXPL, 2, rng.randrange(60))
        st.poke(sm.CLOCK, 2, rng.randrange(360, 1000))
        sm.cancel(st.m)
        s.call(0x482e, stops=[0x310c])
        sc.regions('cancel $482e', st.m, s.read)
    # the supply update after a blast
    changed = {}
    for a in recs:
        for j in range(m0.u8(a) & 0x7f):
            t = m0.u8(a + 6 + 2 * j) & 0x1f
            if t not in (0xb, 0xc, 0xd):
                continue
            for held in (True, False):
                st = St()
                st.poke(a, 1, (st.m.u8(a) & 0x7f) | (0x80 if held else 0))
                s.call(0xf56e)
                s.call(0xf5e2)
                pre = s.read(*UNITS)
                st.poke(stark + 52, 4, a)
                st.poke(a + 6 + 2 * j, 1, st.m.u8(a + 6 + 2 * j) | 0x40)
                s.call(0x41f6, stops=[0x4272])
                mm = Mem(s.read(0, 0x30000))
                if CTL == 'ruinsupplies':
                    mm.set8(a + 6 + 2 * j, (mm.u8(a + 6 + 2 * j) & 0xe0) | t)
                am.supply(mm, 11)
                am.supply(mm, 12)
                if CTL == 'ruinsupplies':
                    mm.set8(a + 6 + 2 * j, (mm.u8(a + 6 + 2 * j) & 0x60) | 0x10)
                s.call(0xf56e)
                s.call(0xf5e2)
                post = s.read(*UNITS)
                sc.regions('supply after a blast', mm, s.read, [UNITS])
                key = ('held' if held else 'free', '%x' % t)
                c11 = sum(pre[16 * u + 11] != post[16 * u + 11] for u in range(32))
                c12 = sum(pre[16 * u + 12] != post[16 * u + 12] for u in range(32))
                slower = all(post[16 * u + 11] <= pre[16 * u + 11] and post[16 * u + 12] <= pre[16 * u + 12]
                             for u in range(32))
                v = changed.setdefault(key, [0, 0, 0, 0])
                v[0] += 1
                v[1] += c11 > 0
                v[2] += c12 > 0
                v[3] += slower
    s('shutdown')
    for k in sc.n:
        print(f'{k}: {sc.ok[k]}/{sc.n[k]}')
    print('supply after a blast (site, type): blasts, +11 changed, +12 changed, no unit faster')
    for k in sorted(changed):
        print('  ', k, changed[k])
    print('branches:', ' '.join(f'{k}={v}' for k, v in sorted(sm.BRANCH.items())))
    bad = sum(sc.n[k] - sc.ok[k] for k in sc.n)
    print('PASS' if bad == 0 else 'FAIL')


if __name__ == '__main__':
    main()
