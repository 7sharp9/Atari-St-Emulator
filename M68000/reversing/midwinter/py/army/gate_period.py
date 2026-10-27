"""Gate for the period end's own tests (ai.md section 5): the counts `$f374`, PRISONERS `$f3be`, the Morale loss
`$ed88`, the endings `$118ba`/`$118f6` and the radio `$f8d8`, run by the game in `stserver` and checked against
period_model.py call by call.

usage: gate_period.py [control]
Needs $MIDWINTER_WORK (default <root>/scratchpad/midwinter) holding d_team.snap and zuul067.st. Legs:
- natural: The Team's clock icon clicked on d_team.snap (in the REPL, as gate_army.py does), stopped at `$ec8c`; the
  game's own call of each routine, and the SITUATION REPORT's 14 numbers (situation_report.png) against the tables;
- poked (labelled poke): 200 states from that snapshot with random sites' held bits flipped, buildings turned to Ruins,
  characters moved into random buildings of random sites, the rise marks, the clock, the HQ and radio flags set at
  random, and in some states every Radio Station held turned to a Ruin or every Heat Mine's site made held; each routine called on each state.
A control name runs a broken model, which must fail: weights (2 and 10 swapped), anysite (prisoners in a Police
Station of any site), day20 (the 20-day ending only after $7080 minutes).
"""
import os, random, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
root = os.environ.get('M68000_ROOT') or HERE
while not os.path.exists(os.path.join(root, 'tools', 'rdis.py')):
    root = os.path.dirname(root)
WORK = os.environ.get('MIDWINTER_WORK') or os.path.join(root, 'scratchpad', 'midwinter')
DISK = os.path.join(WORK, 'zuul067.st')
DLL = os.path.join(root, 'bin', 'Debug', 'net8.0', 'M68000.dll')
OUT = os.path.join(WORK, 'army', 'gate_period')
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(root, 'tools'))
import period_model as pm  # noqa: E402
from army_model import FEAT, Mem  # noqa: E402
from stclient import StServer  # noqa: E402

OUTREG = [(pm.FREE, 40), (pm.PRISONERS, 2), (pm.LOSS, 2), (pm.HEAT, 6), (pm.MESSAGE, 4), (pm.HQ_GONE, 6),
          (pm.TEAM, 40), (pm.RECS, 32 * 0x4a)]
INREG = [(FEAT, 0x2b16a - FEAT), (pm.CLOCK, 2), (0x2c188, 20), (0x2bad8, 8)]
ROUTINES = [(0xed88, pm.morale_loss), (0xf374, pm.counts), (0xf3be, pm.prisoners), (0x118ba, pm.game_over),
            (0x118f6, pm.heat_mines), (0xf8d8, pm.radio)]
# The Team's clock icon (288,32), as gate_army.py's REPORT leg, stopped at the period end's entry
CLICK = ['mouse move 70 -55', 's 100000', 'mouse move 70 -55', 's 2000000', 'mouse down l', 'u ec8c 3000000']
REPORT = {'HEATMINES': 17, 'DESTROYED FACTORIES': 0, 'SYNTH PLANTS': 0, 'WAREHOUSES': 0, 'RADIO STATIONS': 0,
          'ENEMY UNITS': 0, 'ENEMY VEHICLES': 0, 'PRISONERS': 7, 'HELD FACTORIES': 9, 'HELD SYNTH PLANTS': 8,
          'HELD WAREHOUSES': 5, 'HELD RADIO STATIONS': 3, 'MOBILE UNITS': 32, 'MOBILE VEHICLES': 4067}


def broken(name):
    if name == 'weights':
        real = pm.morale_loss

        def loss(m):
            sup, heat = m.w(pm.SUPPLY), m.w(pm.HEAT)
            real(m)
            s = sum(m.u8(pm.HELD + t) for t in (pm.FACTORY, pm.SYNTH, pm.WAREHOUSE, pm.RADIO_ST))
            h = m.u8(pm.HELD + pm.HEAT_MINE)
            m.setw(pm.LOSS, 10 * max(0, s - sup) + 2 * max(0, h - heat))
        return {0xed88: loss}
    if name == 'anysite':
        def prisoners(m):
            n = 0
            for c in range(32):
                r = pm.RECS + 0x4a * c
                p = int.from_bytes(m.b[r + 52:r + 56], 'big')
                if m.s8(r + 63) >= 0 and p and m.u8(p + 6 + 2 * m.u8(r + 64)) & 0x1f == pm.POLICE:
                    n += 1
            m.setw(pm.PRISONERS, n)
        return {0xf3be: prisoners}
    if name == 'day20':
        def game_over(m):
            if m.w(pm.HQ_GONE):
                pm.set_message(m, pm.MSG_HQ)
                m.setw(pm.OVER, 0xffff)
            elif m.w(pm.CLOCK) > 0x7080:
                pm.set_message(m, pm.MSG_DAYS)
                m.setw(pm.OVER, 0xffff)
        return {0x118ba: game_over}
    sys.exit(f'unknown control {name}')


class Score:
    def __init__(self, s):
        self.s, self.n, self.ok, self.shown = s, {}, {}, 0

    def check(self, m, label):
        diffs = []
        for a, ln in OUTREG:
            got, exp = self.s.read(a, ln), bytes(m.b[a:a + ln])
            diffs += [(hex(a + j), exp[j], got[j]) for j in range(ln) if exp[j] != got[j]]
        self.n[label] = self.n.get(label, 0) + 1
        self.ok[label] = self.ok.get(label, 0) + (not diffs)
        if diffs and self.shown < 6:
            self.shown += 1
            print(f'  {label} differs: {diffs[:6]}')


def mem(s, base):
    m = Mem(base)
    for a, n in OUTREG + INREG:
        m.b[a:a + n] = s.read(a, n)
    return m


def records(m):
    out, a = [], FEAT
    while m.u8(a):
        out.append(a)
        a += 6 + 2 * (m.u8(a) & 0x7f)
    return out


def main():
    models = dict(ROUTINES)
    if len(sys.argv) > 1:
        models.update(broken(sys.argv[1]))
    os.makedirs(OUT, exist_ok=True)
    snap0 = os.path.join(OUT, 'team_ec8c.snap')
    p = subprocess.run(['dotnet', 'exec', DLL, 'resume', os.path.join(WORK, 'd_team.snap'), 'repl', '--disk-a', DISK],
                       input='\n'.join(CLICK + [f'snap {snap0}', 'q']) + '\n', capture_output=True, text=True,
                       cwd=root, env=dict(os.environ, ATARI_NOTRACE='1'))
    if 'state saved' not in p.stdout or 'reached' not in p.stdout:
        sys.exit(f'REPL run to $ec8c failed:\n{p.stdout[-2000:]}{p.stderr[-2000:]}')
    s = StServer(root)
    s('load', snapshot=snap0, disk=DISK)
    base = s.read(0, 0x48000)
    fork = s('fork')['id']
    sc = Score(s)
    # natural: the game's own call of each routine in the period end
    for entry, _ in ROUTINES:
        # `$ec8c` runs at PC $8000ec8c (the action table's flagged jsr), so a bsr target keeps the top bit
        r = s('run', max_steps=3000000, until_pc=[entry, entry | 0x80000000])
        if r['reason'] != 'until':
            sys.exit(f'natural: no call of ${entry:x} ({r})')
        m = mem(s, base)
        models[entry](m)
        ret = int.from_bytes(s.read(s.reg('a7'), 4), 'big')
        s('run', max_steps=400000, until_pc=ret)
        sc.check(m, 'natural')
    m = mem(s, base)
    w = lambda a: m.w(a)  # noqa: E731
    held = lambda t: m.u8(pm.HELD + t)  # noqa: E731
    mine = {'HEATMINES': m.u8(pm.FREE + pm.HEAT_MINE), 'DESTROYED FACTORIES': m.u8(0x2c188 + pm.FACTORY),
            'SYNTH PLANTS': m.u8(0x2c188 + pm.SYNTH), 'WAREHOUSES': m.u8(0x2c188 + pm.WAREHOUSE),
            'RADIO STATIONS': m.u8(0x2c188 + pm.RADIO_ST), 'ENEMY UNITS': w(0x2bad8), 'ENEMY VEHICLES': w(0x2badc),
            'PRISONERS': w(pm.PRISONERS), 'HELD FACTORIES': held(pm.FACTORY), 'HELD SYNTH PLANTS': held(pm.SYNTH),
            'HELD WAREHOUSES': held(pm.WAREHOUSE), 'HELD RADIO STATIONS': held(pm.RADIO_ST),
            'MOBILE UNITS': w(0x2bada), 'MOBILE VEHICLES': w(0x2bade)}
    shown = sum(mine[k] == v for k, v in REPORT.items())
    # poked
    rng = random.Random(1989)
    for state in range(200):
        s('restore', id=fork)
        m = Mem(base)

        def poke(a, width, v):
            v &= (1 << 8 * width) - 1
            s('poke', addr=a, width=width, value=v)
            m.b[a:a + width] = v.to_bytes(width, 'big')
        recs = records(m)
        for a in rng.sample(recs, rng.randrange(0, 120)):
            poke(a, 1, m.u8(a) ^ 0x80)
        for a in rng.sample(recs, rng.randrange(0, 60)):
            j = rng.randrange(m.u8(a) & 0x7f)
            poke(a + 6 + 2 * j, 1, (m.u8(a + 6 + 2 * j) & 0x60) | 0x10)
        for c in rng.sample(range(32), rng.randrange(0, 32)):
            r = pm.RECS + 0x4a * c
            site = rng.choice(recs)
            poke(r + 52, 4, site if rng.random() > 0.05 else 0)
            poke(r + 64, 1, rng.randrange(m.u8(site) & 0x7f))
            poke(r + 63, 1, rng.choice([0xff, 0x80, 8, 0, 5, 0x7f]))
        for a in (pm.SUPPLY, pm.HEAT):
            poke(a, 2, rng.randrange(0, 40))
        poke(pm.CLOCK, 2, rng.choice([0, 480, 0x707f, 0x7080, 0x7081, 0xffff, rng.randrange(0x10000)]))
        poke(pm.HQ_GONE, 2, rng.choice([0, 0, 0xffff]))
        poke(pm.RADIO, 2, rng.choice([0, 0, 1, 0xffff]))
        if rng.random() < 0.3:
            for a in recs:
                if m.u8(a) & 0x80:
                    for j in range(m.u8(a) & 0x7f):
                        if m.u8(a + 6 + 2 * j) & 0x1f == pm.RADIO_ST:
                            poke(a + 6 + 2 * j, 1, (m.u8(a + 6 + 2 * j) & 0x60) | 0x10)
        if rng.random() < 0.2:
            for a in recs:
                if not m.u8(a) & 0x80:
                    for j in range(m.u8(a) & 0x7f):
                        if m.u8(a + 6 + 2 * j) & 0x1f == pm.HEAT_MINE:
                            poke(a, 1, m.u8(a) | 0x80)
        state_fork = s('fork')['id']
        state_mem = bytes(m.b)
        for entry, _ in ROUTINES:
            s('restore', id=state_fork)
            mm = Mem(state_mem)
            # the counts the other routines read are the game's own: compute them first, in both
            if entry != 0xf374:
                pm.counts(mm)
                s.call(0xf374)
            models[entry](mm)
            s.call(entry)
            sc.check(mm, f'${entry:x}')
        s('drop', id=state_fork)
    s('shutdown')
    for k in sc.n:
        print(f'{k}: {sc.ok[k]}/{sc.n[k]}')
    print(f'report numbers from the tables: {shown}/{len(REPORT)}')
    print('branches:', ' '.join(f'{k}={v}' for k, v in sorted(pm.BRANCH.items())))
    bad = sum(sc.n[k] - sc.ok[k] for k in sc.n) + len(REPORT) - shown
    print('PASS' if bad == 0 else 'FAIL')


if __name__ == '__main__':
    main()
