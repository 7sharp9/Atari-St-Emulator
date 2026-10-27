"""Gate for the attacks on the player (ai.md section 4): the launches `$1ffe0` (bomber), `$200e8` (mortar) and `$201e0`
(missile), the odds `$20db4`, and the hit tests of the bomb `$209a0` and the mortar shell `$20776`, run by the game in
`stserver` and checked against attack_model.py call by call; and a natural ski run that shows no site changes hands.

usage: gate_attack.py [control]
A control name runs the gate against a broken model, which must fail: nomask (launches ignore the attack mask),
norate (odds without the character's byte +72), aim (the missile flies at the player instead of along the vehicle's
heading), radius (the bomb hits within 180 instead of 200), ahead (the shell aims 180 ahead of the camera, as the bomb
does).
Needs $MIDWINTER_WORK (default <root>/scratchpad/midwinter) holding d_ski.snap and zuul067.st. Legs:
- launch (labelled poke): BOMBERS/MORTARS on and off, every attack mask, the attacker object free, done or running,
  the odds word -1 (draw new odds) or 1, 2, 7, four seeds, random camera and heading; `$1ffe0` and `$200e8`;
- odds (labelled poke): `$20db4` over an 11 x 11 grid of terrain targets, four characters and three vehicle divisors
  (one small enough to overflow the `divu`);
- missile: the game's own calls of `$201e0` over a natural run from d_ski.snap (the engaged vehicle's script), and
  poked: TRAINING on and off, every mask, the missile object free or running, four headings;
- hits (labelled poke): the bomb put at a 19 x 19 grid of offsets (0 to 400 each way, straddling 200) around its aim point, four headings, landing this
  frame, plus falling bombs; the mortar shell at the same offsets around the camera;
- natural: from d_ski.snap until something sets `$14dfc` (a missile from the engaged vehicle, at frame 170), with every
  write to the feature list `$2a150..$2b169` recorded (the bomber's script runs each frame).
Compares the four objects `$1cd7e..$1ce2d` and every global the routines write, and the RNG seed.
"""
import os, random, sys

HERE = os.path.dirname(os.path.abspath(__file__))
root = os.environ.get('M68000_ROOT') or HERE
while not os.path.exists(os.path.join(root, 'tools', 'rdis.py')):
    root = os.path.dirname(root)
WORK = os.environ.get('MIDWINTER_WORK') or os.path.join(root, 'scratchpad', 'midwinter')
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(root, 'tools'))
import attack_model as at  # noqa: E402
from army_model import Mem, SEED  # noqa: E402
from stclient import StServer  # noqa: E402

OUT = [(at.OBJS, 4 * 44), (at.A0E0, 6), (at.COPY_B, 8), (at.Q, 12), (at.HIT, 2), (0x6a34, 2), (0x6a76, 2),
       (0x6a87, 1), (0x6aaf, 1), (0x1f8bc, 2), (at.FALL, 2), (0x206ea, 4), (SEED, 2)]
INPUT = [(at.CAMX, 8), (at.HEAD, 2), (at.TX, 4), (at.CHAR, 2), (at.MASK, 1), (at.BOMBERS, 6), (at.DIVISOR, 2)]
FEATURES = (0x2a150, 0x2b169)
OFFSETS = [0, 50, 100, 180, 195, 199, 200, 210, 300, 400]
OFFSETS = sorted({-o for o in OFFSETS} | set(OFFSETS))  # straddles the 200 hit radius


class Gate:
    def __init__(self):
        self.s = StServer(root)
        self.s('load', snapshot=os.path.join(WORK, 'd_ski.snap'), disk=os.path.join(WORK, 'zuul067.st'))
        self.base = self.s.read(0, 0x48000)
        self.fork = self.s('fork')['id']
        self.n, self.ok, self.shown = {}, {}, 0

    def mem(self, fresh=False):
        m = Mem(self.base)
        if fresh:
            for a, n in OUT + INPUT:
                m.b[a:a + n] = self.s.read(a, n)
        return m

    def poke(self, m, a, width, v):
        self.s('poke', addr=a, width=width, value=v & ((1 << 8 * width) - 1))
        m.b[a:a + width] = (v & ((1 << 8 * width) - 1)).to_bytes(width, 'big')

    def check(self, m, label):
        diffs = []
        for a, ln in OUT:
            got, exp = self.s.read(a, ln), bytes(m.b[a:a + ln])
            diffs += [(hex(a + j), exp[j], got[j]) for j in range(ln) if exp[j] != got[j]]
        self.n[label] = self.n.get(label, 0) + 1
        self.ok[label] = self.ok.get(label, 0) + (not diffs)
        if diffs and self.shown < 6:
            self.shown += 1
            print(f'  {label} differs: {diffs[:6]}')

    def call(self, entry, model, label, **regs):
        self.s('restore', id=self.fork)
        m = self.mem()
        yield m
        model(m)
        self.s.call(entry, **regs)
        self.check(m, label)


def scenario(g, m, rng):
    g.poke(m, at.CAMX, 4, rng.randrange(0x40000, 0x2c0000))
    g.poke(m, at.CAMY, 4, rng.randrange(0x40000, 0x2c0000))
    g.poke(m, at.HEAD, 2, rng.randrange(0, 0x400, 2))


def run_call(g, entry, model, label, setup, **regs):
    gen = g.call(entry, model, label, **regs)
    m = next(gen)
    setup(m)
    next(gen, None)


def broken(name):
    """Patch attack_model into one of the wrong readings the gate must reject."""
    if name == 'nomask':
        real_launch = at.launch
        at.launch = lambda m, flag, bit, *a: (m.set8(at.MASK, 0xff), real_launch(m, flag, bit, *a))
    elif name == 'norate':
        real_u8 = Mem.u8
        Mem.u8 = lambda m, a: 0 if at.RECS <= a < at.RECS + 32 * 0x4a and (a - at.RECS) % 0x4a == 72 else real_u8(m, a)
    elif name == 'aim':
        real_missile = at.missile

        def missile(m, a5):
            before = at.BRANCH.get('missile', 0)
            real_missile(m, a5)
            if at.BRANCH.get('missile', 0) > before:
                o = at.SHELL
                dx, dy = at.direction(at.l(m, o + 28) - at.l(m, o + 6), at.l(m, o + 32) - at.l(m, o + 10))
                m.setw(o + 24, dx)
                m.setw(o + 26, dy)
        at.missile = missile
    elif name == 'radius':
        real_near = at.near
        at.near = lambda m, o, r: real_near(m, o, 0xb4 if r == 0xc8 else r)
    elif name == 'ahead':
        real_polar, real_shell = at.polar, at.shell

        def shell(m):
            real_shell(m)
            x, y = real_polar(m, m.w(at.HEAD), 0xb4, at.l(m, at.CAMX), at.l(m, at.CAMY))
            at.setl(m, at.SHELL + 28, x)
            at.setl(m, at.SHELL + 32, y)
            m.setw(at.HIT, 1 if at.near(m, at.SHELL, 0xc8) else 0)
        at.shell = shell
    else:
        sys.exit(f'unknown control {name}')


def main():
    if len(sys.argv) > 1:
        broken(sys.argv[1])
    g = Gate()
    rng = random.Random(1989)
    # launch
    for entry, model, flag, oddsw, name in ((0x1ffe0, at.bomber, at.BOMBERS, at.ODDS_B, '$1ffe0 bomber'),
                                            (0x200e8, at.mortar, at.MORTARS, at.ODDS_M, '$200e8 mortar')):
        for on in (0, 0xffff):
            for mask in range(8):
                for st in (0xffff, 0, 1):
                    for odds in (0xffff, 1, 2, 7):
                        for seed in (1, 0x1234, 0x8001, 0xfffe):
                            def setup(m):
                                g.poke(m, flag, 2, on)
                                g.poke(m, at.MASK, 1, mask)
                                g.poke(m, at.BOMBER + 38, 2, st)
                                g.poke(m, oddsw, 2, odds)
                                g.poke(m, SEED, 2, seed)
                                scenario(g, m, rng)
                            run_call(g, entry, model, name, setup)
    # odds
    for tx in range(0, 0x1600, 0x200):
        for ty in range(0, 0x1600, 0x200):
            for ch in (0, 9, 14, 21):
                for div in (0x1e, 1, 300):
                    def setup(m):
                        g.poke(m, at.TX, 2, tx)
                        g.poke(m, at.TY, 2, ty)
                        g.poke(m, at.CHAR, 2, ch)
                        g.poke(m, at.DIVISOR, 2, div)
                        g.poke(m, SEED, 2, rng.randrange(1, 0xffff))
                    run_call(g, 0x20db4, at.odds, '$20db4 odds', setup)
    # missile, poked
    for tr in (0, 0xffff):
        for mask in range(8):
            for st in (0xffff, 1):
                for _ in range(4):
                    def setup(m):
                        g.poke(m, at.TRAINING, 2, tr)
                        g.poke(m, at.MASK, 1, mask)
                        g.poke(m, at.SHELL + 38, 2, st)
                        scenario(g, m, rng)
                    run_call(g, 0x201e0, lambda m: at.missile(m, at.ENGAGED), '$201e0 missile poked', setup,
                             a5=at.ENGAGED)
    # hits
    for head in (0, 0x100, 0x2a4, 0x3fe):
        for dx in OFFSETS:
            for dy in OFFSETS:
                def setup(m):
                    g.poke(m, at.HEAD, 2, head)
                    ax, ay = at.polar(m, head, 0xb4, at.l(m, at.CAMX), at.l(m, at.CAMY))
                    g.poke(m, at.SHELL + 6, 4, ax + dx)
                    g.poke(m, at.SHELL + 10, 4, ay + dy)
                    g.poke(m, at.SHELL + 36, 2, 5)
                    g.poke(m, at.SHELL + 38, 2, 1)
                    g.poke(m, at.FALL, 2, 0)
                    g.poke(m, at.HIT, 2, 0)
                run_call(g, 0x209a0, at.bomb, '$209a0 bomb', setup, a5=at.SHELL)
    for _ in range(50):
        def setup(m):
            scenario(g, m, rng)
            g.poke(m, at.SHELL + 36, 2, rng.randrange(100, 2000))
            g.poke(m, at.SHELL + 22, 2, rng.randrange(0, 0x800))
            g.poke(m, at.SHELL + 24, 2, rng.randrange(0, 0x10000))
            g.poke(m, at.SHELL + 26, 2, rng.randrange(0, 0x10000))
            g.poke(m, at.FALL, 2, rng.randrange(0, 60))
        run_call(g, 0x209a0, at.bomb, '$209a0 bomb', setup, a5=at.SHELL)
    for dx in OFFSETS:
        for dy in OFFSETS:
            def setup(m):
                g.poke(m, at.SHELL + 6, 4, at.l(m, at.CAMX) + dx)
                g.poke(m, at.SHELL + 10, 4, at.l(m, at.CAMY) + dy)
                g.poke(m, at.HIT, 2, 0)
            run_call(g, 0x20776, at.shell, '$20776 shell', setup)
    # natural: the game's own missile launches, and the feature list over the run
    g.s('restore', id=g.fork)
    feat = g.s('watch_add', lo=FEATURES[0], hi=FEATURES[1], kind='w')['id']
    hitw = g.s('watch_add', lo=at.HIT, hi=at.HIT + 1, kind='w', stop=True)['id']
    frames = scripts = 0
    BPS = [0x12a5e, 0x2040e, 0x201e0]
    g.s('bp_set', addrs=BPS)
    while True:
        r = g.s('run', max_steps=2000000)
        if r['reason'] == 'watch':
            break
        if r['reason'] != 'breakpoint' or frames > 200:
            sys.exit(f'natural run stopped: {r}')
        pc = g.s.reg('pc')
        if pc == 0x12a5e:
            frames += 1
        elif pc == 0x2040e:
            scripts += 1
        else:
            g.s('bp_clear', addrs=BPS)
            m = g.mem(fresh=True)
            at.missile(m, g.s.reg('a5'))
            ret = int.from_bytes(g.s.read(g.s.reg('a7'), 4), 'big')
            g.s('run', max_steps=200000, until_pc=ret)
            g.check(m, '$201e0 missile natural')
            g.s('bp_set', addrs=BPS)
    ends = [(e['pc'], e['value']) for w in g.s('watch_events', id=hitw) for e in w['events']]
    fw = sum(len(w['events']) for w in g.s('watch_events', id=feat))
    g.s('shutdown')
    for k in g.n:
        print(f'{k}: {g.ok[k]}/{g.n[k]}')
    print(f'natural: {frames} frames, bomber script {scripts}, feature-list writes {fw}; the trip ends: {ends}')
    print('branches:', ' '.join(f'{k}={v}' for k, v in sorted(at.BRANCH.items())))
    bad = sum(g.n[k] - g.ok[k] for k in g.n)
    print('PASS' if bad == 0 and fw == 0 else 'FAIL')


if __name__ == '__main__':
    main()
