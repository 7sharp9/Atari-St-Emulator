"""Gate for the player's side of combat (the engagement, the player's launchers and shots, the kill flag's tumble into
`$cbbe`, the sniping pick, the engaged vehicle's fire odds and fire), run by the game in `stserver` and checked
against shot_model.py call by call.

usage: gate_shot.py [control]
A control name runs the gate against a broken model, which must fail:
  clobber the lower slots boxed against the camera after an engagement (the game boxes them against kind * 4)
  box     the engagement box 33 wide instead of 32
  radius  the ski shot kills within 160 instead of 150
  ammo    the launchers fire with no round left
  wait    a launch leaves the vehicle's fire wait `$1fba0` alone
  land    the ski shot lands when its height reaches 0 or below (the game tests = 0)
  snap    the steering never snaps onto the aim (always turns by the rate)
  tumble  the tumble ends at +18 >= $200 instead of = $200
  odds    no command-vehicle override of the vehicle's odds (n = 5, wait 30)
Needs $MIDWINTER_WORK (default <root>/scratchpad/midwinter) holding d_ski.snap and zuul067.st. Every leg is a
labelled poke of d_ski.snap's state, then one call of the game's routine (`s.call`).
"""
import os, random, sys

HERE = os.path.dirname(os.path.abspath(__file__))
root = os.environ.get('M68000_ROOT') or HERE
while not os.path.exists(os.path.join(root, 'tools', 'rdis.py')):
    root = os.path.dirname(root)
WORK = os.environ.get('MIDWINTER_WORK') or os.path.join(root, 'scratchpad', 'midwinter')
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(root, 'tools'))
import shot_model as sm  # noqa: E402
from shot_model import Mem, l  # noqa: E402
from stclient import StServer  # noqa: E402
import attack_model as at  # noqa: E402

OUT = [(sm.SHOT, 4 * 44), (0x14132, 10), (sm.TARGET, 4), (sm.RATE, 8), (sm.RADIUS, 2), (0x1f95e, 2), (0x6368, 4),
       (0x6a34, 0x7c), (0x25132, 0x16), (sm.HOLD, 8), (sm.ENGAGED, 4), (sm.WINDOW, 2), (sm.REQ, 2),
       (sm.ENG_KIND, 2), (sm.SLOTS, 41 * 16), (0xd5d8, 2), (0x206ea, 4), (0x200e0, 6)]
# radii the shots test, each straddled
EDGES = [0, 74, 75, 76, 99, 100, 101, 149, 150, 151, 159, 160, 799, 800, 801, 999, 1000, 1001, 1999, 2000, 2001, 2500]


class Gate:
    def __init__(self):
        self.s = StServer(root)
        self.s('load', snapshot=os.path.join(WORK, 'd_ski.snap'), disk=os.path.join(WORK, 'zuul067.st'))
        self.base = self.s.read(0, 0x48000)
        self.fork = self.s('fork')['id']
        self.n, self.ok, self.shown = {}, {}, 0

    def poke(self, m, a, width, v):
        v &= (1 << 8 * width) - 1
        self.s('poke', addr=a, width=width, value=v)
        m.b[a:a + width] = v.to_bytes(width, 'big')

    def check(self, m, label, extra_ok=True):
        diffs = []
        for a, ln in OUT:
            got, exp = self.s.read(a, ln), bytes(m.b[a:a + ln])
            diffs += [(hex(a + j), exp[j], got[j]) for j in range(ln) if exp[j] != got[j]]
        good = not diffs and extra_ok
        self.n[label] = self.n.get(label, 0) + 1
        self.ok[label] = self.ok.get(label, 0) + good
        if not good and self.shown < 8:
            self.shown += 1
            print(f'  {label} differs: {diffs[:6]} {"" if extra_ok else "(stop pc)"}')

    def run(self, entry, model, label, setup, stops=(), **regs):
        self.s('restore', id=self.fork)
        m = Mem(self.base)
        setup(m)
        want = model(m)
        r = self.s.call(entry, stops=stops, **regs)
        extra = True
        if stops:
            pc = self.s.reg('pc')
            extra = (pc in stops) == bool(want)
        self.check(m, label, extra)


def put_dir(g, m, o, head):
    sx, sy = sm.sincos(m, head)
    g.poke(m, o + 24, 2, sx)
    g.poke(m, o + 26, 2, sy)


def broken(name):
    if name == 'box':
        real = sm.engage
        sm.engage = lambda m, box=0x20: real(m, 0x21)
    elif name == 'radius':
        sm.near = lambda m, o, r: at.near(m, o, 0xa0 if r == 0x96 else r)
    elif name == 'ammo':
        real = sm.launch

        def launch(m, entry):
            a = sm.LAUNCHERS[entry][0]
            if m.w(a) == 0:
                m.setw(a, 1)
            real(m, entry)
        sm.launch = launch
    elif name == 'wait':
        real = sm.launch

        def launch(m, entry):
            w = m.w(sm.FIRE_WAIT)
            real(m, entry)
            m.setw(sm.FIRE_WAIT, w)
        sm.launch = launch
    elif name == 'land':
        real = sm.ski_shot

        def ski(m, o=sm.SHOT):
            if m.sw(o + 36) - 4 < 0:
                m.setw(o + 36, 4)
            real(m, o)
        sm.ski_shot = ski
        sm.SCRIPTS[0x208d6] = ski
    elif name == 'clobber':
        sm.CLOBBER = False
    elif name == 'snap':
        sm.SNAP = False
    elif name == 'tumble':
        real = sm.tumble

        def tumble(m):
            if m.w(sm.KILL) and 0x200 < m.w(sm.VEH + 18) < 0x400:
                m.setw(sm.VEH + 18, 0x200)
            return real(m)
        sm.tumble = tumble
    elif name == 'odds':
        real = sm.veh_odds

        def odds(m):
            k = sm.SLOTS + ((m.w(sm.ENGAGED) << 4) & 0xffff) + 8
            was = m.w(k)
            if m.sw(k) < 0:
                m.setw(k, 5)
            real(m)
            m.setw(k, was)
        sm.veh_odds = odds
    else:
        sys.exit(f'unknown control {name}')


def main():
    if len(sys.argv) > 1:
        broken(sys.argv[1])
    g = Gate()
    rng = random.Random(1989)

    def camera(m):
        g.poke(m, sm.CAMX, 4, rng.randrange(0x40000, 0x2c0000))
        g.poke(m, sm.CAMY, 4, rng.randrange(0x40000, 0x2c0000))
        g.poke(m, sm.HEAD, 2, rng.randrange(0, 0x400, 2))

    # 1. the engagement $ca7e: random slot tables around the camera's grid cell, offsets straddling the box edges
    offs = [-18, -17, -16, -15, -1, 0, 1, 14, 15, 16, 17]
    for trial in range(400):
        def setup(m):
            if trial % 2:
                camera(m)
            g.poke(m, sm.WINDOW, 2, -1 if trial % 37 == 0 else rng.randrange(32))
            g.poke(m, sm.ENGAGED, 2, -1 if rng.random() < 0.7 else rng.randrange(41))
            gx, gy = sm.to_grid(m, l(m, sm.CAMX), l(m, sm.CAMY))
            for i in range(41):
                s = sm.SLOTS + 16 * i
                act = rng.random() < 0.5
                g.poke(m, s, 4, rng.choice([0, 1, 0x2d700]) if act else 0xffffffff)
                near = rng.random() < 0.6
                dx = rng.choice(offs) if near else rng.randrange(-200, 200)
                dy = rng.choice(offs) if near else rng.randrange(-200, 200)
                g.poke(m, s + 4, 2, gx + dx)
                g.poke(m, s + 6, 2, gy + dy)
                g.poke(m, s + 8, 2, rng.choice([-1, 0, 1, 2, 3, 4]))
                g.poke(m, s + 12, 2, -1 if rng.random() < 0.2 else 0)
                g.poke(m, s + 14, 2, -1 if rng.random() < 0.3 else 0)
        g.run(0xca7e, sm.engage, '$ca7e engage', setup)

    # 2. the launchers: rounds 0/1/20, the shot object free, done or flying, the vehicle's fire wait set
    for entry in sm.LAUNCHERS:
        ammo = sm.LAUNCHERS[entry][0]
        for rounds in (0, 1, 20):
            for st in (-1, 0, 1):
                for _ in range(4):
                    def setup(m):
                        camera(m)
                        g.poke(m, ammo, 2, rounds)
                        g.poke(m, sm.SHOT + 38, 2, st)
                        g.poke(m, sm.SPEED, 2, rng.randrange(0, 0x300))
                        g.poke(m, sm.FIRE_WAIT, 2, rng.randrange(1, 40))
                        g.poke(m, 0x1721c, 2, rng.randrange(0, 0x400))
                    g.run(entry, lambda m, e=entry: sm.launch(m, e), f'${entry:x} launch', setup)

    # 3. the shots' scripts: the shot at offsets straddling every radius from the engaged vehicle, the vehicle active
    #    or not, random direction and speed; the ski shot at heights straddling its landing; the far test at 5000
    signed = sorted({-e for e in EDGES} | set(EDGES))
    for script, fn in sm.SCRIPTS.items():
        for k in range(700):
            def setup(m):
                camera(m)
                o, v = sm.SHOT, sm.VEH
                g.poke(m, v + 6, 4, l(m, sm.CAMX) + rng.randrange(-3000, 3000))
                g.poke(m, v + 10, 4, l(m, sm.CAMY) + rng.randrange(-3000, 3000))
                g.poke(m, v + 38, 2, -1 if k % 9 == 0 else 1)
                if k % 13 == 5:  # the far test: the shot 4999..5001 from the camera
                    g.poke(m, o + 6, 4, l(m, sm.CAMX) + rng.choice([-5001, -5000, -4999, 4999, 5000, 5001, 0]))
                    g.poke(m, o + 10, 4, l(m, sm.CAMY) + rng.choice([-5001, -5000, 4999, 5000, 5001, 0]))
                else:
                    g.poke(m, o + 6, 4, l(m, v + 6) + rng.choice(signed))
                    g.poke(m, o + 10, 4, l(m, v + 10) + rng.choice(signed))
                put_dir(g, m, o, rng.randrange(0, 0x400, 2))
                g.poke(m, o + 22, 2, rng.choice([0x64, 0x1c1, 0x1c2, 0x1c3, 0x258, 0x63f, 0x640, 0x641, 0x700]))
                g.poke(m, o + 36, 2, rng.choice([4, 8, 40, 2, 6, 0x28]) if script == 0x208d6 else
                       rng.randrange(0, 60))
                g.poke(m, o + 18, 2, rng.randrange(0, 0x10000))
                g.poke(m, o + 20, 2, rng.randrange(0, 0x10000))
                g.poke(m, o + 38, 2, 1)
            g.run(script, lambda m, f=fn: f(m), f'${script:x} shot', setup, a5=sm.SHOT)

    # 3b. every script's two radii straddled on both axes at once (the vehicle active), random direction
    for script, fn, radii in ((0x208d6, sm.ski_shot, (150, 1000)), (0x20a52, sm.gun_shot, (75, 800)),
                              (0x207c4, sm.rocket, (100, 2000))):
        for r in radii:
            grid = [0, r - 1, r, r + 1, 1 - r, -r, -r - 1]
            for dx in grid:
                for dy in grid:
                    def setup(m):
                        camera(m)
                        o, v = sm.SHOT, sm.VEH
                        g.poke(m, v + 6, 4, l(m, sm.CAMX) + rng.randrange(-2000, 2000))
                        g.poke(m, v + 10, 4, l(m, sm.CAMY) + rng.randrange(-2000, 2000))
                        g.poke(m, v + 38, 2, 1)
                        g.poke(m, o + 6, 4, l(m, v + 6) + dx)
                        g.poke(m, o + 10, 4, l(m, v + 10) + dy)
                        put_dir(g, m, o, rng.randrange(0, 0x400, 2))
                        g.poke(m, o + 22, 2, 0x258)
                        g.poke(m, o + 36, 2, 0x28)
                        g.poke(m, o + 38, 2, 1)
                    g.run(script, lambda m, f=fn: f(m), f'${script:x} shot', setup, a5=sm.SHOT)

    # 4. the tumble $141ce up to the kill $cbbe (the call is stopped at $cbbe's entry)
    for flag in (0, 1):
        for r18 in (0, 0x40, 0x1c0, 0x200, 0x10, 0x240, 0x3c0, 0x3fe):
            for _ in range(3):
                def setup(m):
                    g.poke(m, sm.KILL, 2, flag)
                    g.poke(m, sm.VEH + 18, 2, r18)
                    g.poke(m, sm.VEH + 20, 2, rng.randrange(0, 0x400))
                    g.poke(m, 0x1f95e, 2, 1)
                g.run(0x141ce, sm.tumble, '$141ce tumble', setup, stops=(0xcbbe,))

    # 5. the sniping pick $14150, and the explosion $20728 on each target
    for pick in (0, -1, -2, -3, -4, -5, 5):
        for _ in range(3):
            def setup(m):
                g.poke(m, sm.PICK, 2, pick)
                for o in (sm.VEH, sm.AIR, sm.PROJ):
                    g.poke(m, o + 38, 2, rng.choice([-1, 1]))
            g.run(0x14150, sm.snipe_hit, '$14150 snipe', setup)
    for tgt in (sm.VEH, sm.AIR, sm.PROJ):
        for _ in range(3):
            def setup(m):
                g.poke(m, sm.TARGET, 4, tgt)
                g.poke(m, tgt + 6, 4, rng.randrange(0, 0x400000))
                g.poke(m, tgt + 10, 4, rng.randrange(0, 0x400000))
                g.poke(m, tgt + 36, 2, rng.randrange(0, 0x400))
                g.poke(m, sm.SHOT + 38, 2, 1)
            g.run(0x20728, sm.explosion, '$20728 explosion', setup)

    # 6. the engaged vehicle's odds $1faa6
    for k in range(300):
        def setup(m):
            g.poke(m, sm.CHAR, 2, rng.choice([14, 0, 9, 21, 31]))
            g.poke(m, sm.ENG_UNIT, 2, rng.randrange(32))
            g.poke(m, sm.UNITS + 16 * m.w(sm.ENG_UNIT) + 12, 1, rng.choice([0, 1, 19, 200, 255]))
            g.poke(m, sm.VW1, 2, rng.choice([0x1388, 0x100, 0xffff, 0x8000, 0x7fff, 300]))
            g.poke(m, sm.VW2, 2, rng.randrange(0, 0x40))
            g.poke(m, sm.VW3, 2, rng.randrange(0, 0x40))
            e = rng.randrange(41)
            g.poke(m, sm.ENGAGED, 2, e)
            g.poke(m, sm.SLOTS + 16 * e + 8, 2, rng.choice([-1, 0, 1, 2, 3, 4, 5]))
            g.poke(m, 0xd5d8, 2, rng.randrange(1, 0xffff))
        g.run(0x1faa6, sm.veh_odds, '$1faa6 odds', setup)

    # 7. the vehicle's fire, the tail $20cfe of its script (A5 = the vehicle)
    for wait in (0, 1, 30):
        for odds in (1, 2, 5, 10015):
            for tr in (0, 0xffff):
                for st in (-1, 1):
                    for _ in range(3):
                        def setup(m):
                            camera(m)
                            g.poke(m, sm.FIRE_WAIT, 2, wait)
                            g.poke(m, sm.ODDS, 2, odds)
                            g.poke(m, at.TRAINING, 2, tr)
                            g.poke(m, sm.PROJ + 38, 2, st)
                            g.poke(m, 0xd5d8, 2, rng.randrange(1, 0xffff))
                        g.run(0x20cfe, sm.veh_fire, '$20cfe vehicle fire', setup, a5=sm.VEH)

    g.s('shutdown')
    for k in g.n:
        print(f'{k}: {g.ok[k]}/{g.n[k]}')
    print('branches:', ' '.join(f'{k}={v}' for k, v in sorted(sm.BRANCH.items())))
    bad = sum(g.n[k] - g.ok[k] for k in g.n)
    print('PASS' if bad == 0 else 'FAIL')


if __name__ == '__main__':
    main()
