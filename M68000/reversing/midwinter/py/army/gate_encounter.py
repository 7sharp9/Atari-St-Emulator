"""Gate for the encounter model (ai.md section 3): the search `$c2f0` and the per-frame `$c4f2`, run by the game in
`stserver` and checked against encounter_model.py call by call.

usage: gate_encounter.py [frames] [chain] [controls]
Needs $MIDWINTER_WORK (default <root>/scratchpad/midwinter) holding d_decisions.snap, d_ski.snap and zuul067.st. Two legs:
- entry: the ski icon clicked on d_decisions.snap (drive.txt's click, made in the REPL: stserver's `mouse` does
  not register in this game), stopped at the 3D entry's `$c2f0`; that call and the `$c4f2` calls after it;
- natural: from d_ski.snap (3D view, unit 27 in the window, slot 0 engaged) the game's own calls of `$c2f0` and
  `$c4f2` over `frames` calls, each compared from its entry state (the unsteered skier crashes after 170 frames,
  so `frames` <= 165; slot 23 becomes the engaged one on the way);
- poked (labelled poke): for every active unit, the terrain target `$19cd4/$19cd6` is set so the unit lies in the
  window (three offsets), with `$2bae0` (engaged slot) -1, then `$c2f0` is called and `chain` calls of `$c4f2`
  follow, each from a planted return address with interrupts masked.
Compares the 41 object slots, the script, the encounter words `$2bad4..$2bb36`, `$d57c` and the RNG seed.
"""
import os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
root = os.environ.get('M68000_ROOT') or HERE
while not os.path.exists(os.path.join(root, 'tools', 'rdis.py')):
    root = os.path.dirname(root)
WORK = os.environ.get('MIDWINTER_WORK') or os.path.join(root, 'scratchpad', 'midwinter')
DISK = os.path.join(WORK, 'zuul067.st')
DLL = os.path.join(root, 'bin', 'Debug', 'net8.0', 'M68000.dll')
OUT = os.path.join(WORK, 'army', 'gate_encounter')
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(root, 'tools'))
import army_model as am  # noqa: E402
import encounter_model as em  # noqa: E402
from stclient import StServer  # noqa: E402

REGIONS = [(em.SLOTS, 41 * 16), (em.SCRIPT, 1024), (0x2bad4, 0x2bb36 - 0x2bad4), (em.ROOM, 2), (am.SEED, 2)]
INPUTS = [(am.UNITS, 512), (am.NODES, 384), (am.MULT, 2), (em.GRID, 10000), (em.TX, 4)]


def load_mem(s):
    m = am.Mem(bytes(0x48000))
    for a, n in REGIONS + INPUTS:
        m.b[a:a + n] = s.read(a, n)
    return m


class Score:
    def __init__(self):
        self.n = {}
        self.ok = {}
        self.bad = 0

    def check(self, s, pre, entry, label):
        model = am.Mem(pre.b)
        (em.search if entry == 0xc2f0 else em.frame)(model)
        diffs = []
        for a, ln in REGIONS:
            got, exp = s.read(a, ln), bytes(model.b[a:a + ln])
            diffs += [(hex(a + j), exp[j], got[j]) for j in range(ln) if exp[j] != got[j]]
        k = f'${entry:x}'
        self.n[k] = self.n.get(k, 0) + 1
        self.ok[k] = self.ok.get(k, 0) + (not diffs)
        if diffs and self.bad < 5:
            self.bad += 1
            print(f'{label} mismatch (addr, model, game): {diffs[:10]}')

    def report(self, name):
        print(name + ': ' + ', '.join(f'{k} {self.ok[k]}/{self.n[k]}' for k in sorted(self.n)))


def entry_snap():
    """d_decisions.snap with drive.txt's ski-icon click made through the REPL, stopped at the first `$c2f0`."""
    snap = os.path.join(OUT, 'entry_c2f0.snap')
    lines = ['mouse move -31 -2', 's 600000', 'mouse down l', 'u c2f0 20000000', f'snap {snap}', 'q']
    p = subprocess.run(['dotnet', 'exec', DLL, 'resume', os.path.join(WORK, 'd_decisions.snap'), 'repl', '--disk-a',
                        DISK], input='\n'.join(lines) + '\n', capture_output=True, text=True, cwd=root,
                       env=dict(os.environ, ATARI_NOTRACE='1'))
    if 'state saved' not in p.stdout or 'reached' not in p.stdout:
        sys.exit(f'REPL run to the first $c2f0 failed:\n{p.stdout[-2000:]}{p.stderr[-2000:]}')
    return snap


def natural(s, frames, start, name):
    s('load', snapshot=start, disk=DISK)
    first = s.reg('pc') == 0xc2f0
    sc = Score()
    for i in range(frames):
        r = {'reason': 'until'} if first else s('run', max_steps=3000000, until_pc=[0xc2f0, 0xc4f2])
        first = False
        if r['reason'] != 'until':
            sys.exit(f'natural: stopped after {i} calls ({r})')
        pc, pre = s.reg('pc'), load_mem(s)
        ret = int.from_bytes(s.read(s.reg('a7'), 4), 'big')
        r = s('run', max_steps=400000, until_pc=ret)
        if r['reason'] != 'until':
            sys.exit(f'natural call at ${pc:x}: no return ({r})')
        sc.check(s, pre, pc, f'natural call {i}')
    sc.report(f'natural calls from {name} ({frames})')


def poked(s, chain):
    sc = Score()
    s('load', snapshot=os.path.join(WORK, 'd_ski.snap'), disk=DISK)
    base = s('fork')
    base = base['id'] if isinstance(base, dict) else base
    units = s.read(am.UNITS, 512)
    for u in range(32):
        if not units[16 * u + 4] & 0x80:
            continue
        x, y = int.from_bytes(units[16 * u:16 * u + 2], 'big'), int.from_bytes(units[16 * u + 2:16 * u + 4], 'big')
        for off in (-40, 0, 40):
            s('restore', id=base)
            s.sp = None
            s('poke', addr=em.TX, width=2, value=(x // 2 + off) & 0xffff)
            s('poke', addr=em.TY, width=2, value=(y // 2 - off) & 0xffff)
            s('poke', addr=em.ENGAGED, width=4, value=0xffffffff)
            pre = load_mem(s)
            s.call(0xc2f0, a6=0x2c376)
            sc.check(s, pre, 0xc2f0, f'unit {u} off {off} search')
            for k in range(chain):
                pre = load_mem(s)
                try:
                    s.call(0xc4f2, a6=0x2c376)
                except SystemExit as e:
                    print(f'unit {u} off {off} frame {k}: {e}')
                    break
                sc.check(s, pre, 0xc4f2, f'unit {u} off {off} frame {k}')
    sc.report(f'poked: every active unit x 3 targets, {chain} frames each')


def empty(s):
    """A target with no unit in its window: `$2baec` = -1 and nothing else changes."""
    sc = Score()
    s('load', snapshot=os.path.join(WORK, 'd_ski.snap'), disk=DISK)
    s.sp = None
    for t in (0, 1000):
        s('poke', addr=em.TX, width=4, value=t * 0x10001)
        pre = load_mem(s)
        s.call(0xc2f0, a6=0x2c376)
        sc.check(s, pre, 0xc2f0, f'empty window {t}')
    sc.report('no unit in the window')


def controls(s, chain):
    """Broken models must fall short: no random turn and tankers drawn before bulls (poked leg); every kind costing
    1 strength and no leader cascade (kill leg)."""
    turn, spawn = em.turn, em.spawn
    em.turn = lambda m, i: None
    poked(s, chain)
    em.turn = turn
    em.CNT[0], em.CNT[1] = em.CNT[1], em.CNT[0]
    poked(s, chain)
    em.CNT[0], em.CNT[1] = em.CNT[1], em.CNT[0]
    em.DOUBLE_COST = 5
    kills(s)
    em.DOUBLE_COST, em.CASCADE = 3, False
    kills(s)
    em.CASCADE = True


KILL_REGIONS = [(am.UNITS, 512), (em.SLOTS, 41 * 16), (0x2bad8, 8), (0x2baec, 2), (0x2bae0, 4), (0x2bb24, 4),
                (0x2c116, 0x2c132 - 0x2c116), (em.NOSUM, 4)]


def kills(s):
    """`$cbbe` for every unit: its own object (slot 0) and a vehicle of each kind at strengths 1, 2 and 36, stopped
    at the radio message `$cd6e` or the return. Also checks the live-vehicle counter against the unit table."""
    s('load', snapshot=os.path.join(WORK, 'd_ski.snap'), disk=DISK)
    s.sp = None
    base = s('fork')
    base = base['id'] if isinstance(base, dict) else base
    units = s.read(am.UNITS, 512)
    own = sum(1 for u in range(32) if not units[16 * u + 5] & 0x40)
    veh = sum(units[16 * u + 6 + i] for u in range(32) for i in range(5)) + own
    print(f'live vehicles $2bade = {int.from_bytes(s.read(em.LIVE_VEH, 2), "big")}, unit table sum {veh} '
          f'(+6..+10 of 32 units, plus {own} own vehicles); live units $2bada = '
          f'{int.from_bytes(s.read(em.LIVE_UNITS, 2), "big")}')
    n = ok = 0
    stops = {}
    for u in range(32):
        for slot, cat, strength in [(0, 0, None)] + [(5, c, k) for c in range(5) for k in (1, 2, 36)]:
            s('restore', id=base)
            s('poke', addr=em.ENGAGED, width=2, value=slot)
            s('poke', addr=em.ENGUNIT, width=2, value=u)
            s('poke', addr=em.SLOTS + 16 * slot + 8, width=2, value=cat)
            if strength is not None:
                s('poke', addr=am.UNITS + 16 * u + 14, width=1, value=strength)
            m = am.Mem(bytes(0x48000))
            for a, ln in KILL_REGIONS + [(0x2c132, 128)]:
                m.b[a:a + ln] = s.read(a, ln)
            s.call(0xcbbe, stops=[0xcd6e], a6=0x2c376)
            got = 'message' if s.reg('pc') == 0xcd6e else 'return'
            exp = em.kill(m)
            diffs = [] if got == exp else [('stop', exp, got)]
            for a, ln in KILL_REGIONS:
                g, x = s.read(a, ln), bytes(m.b[a:a + ln])
                diffs += [(hex(a + j), x[j], g[j]) for j in range(ln) if x[j] != g[j]]
            n += 1
            ok += not diffs
            stops[got] = stops.get(got, 0) + 1
            if diffs and n - ok <= 5:
                print(f'kill unit {u} slot {slot} kind {cat} strength {strength}: {diffs[:10]}')
    print(f'kills: {ok}/{n} (stops {stops})')


def main():
    frames = int(sys.argv[1]) if len(sys.argv) > 1 else 165
    chain = int(sys.argv[2]) if len(sys.argv) > 2 else 100
    s = StServer(root)
    os.makedirs(OUT, exist_ok=True)
    natural(s, frames, entry_snap(), 'the ski icon (d_decisions.snap)')
    natural(s, frames, os.path.join(WORK, 'd_ski.snap'), 'd_ski.snap')
    poked(s, chain)
    empty(s)
    kills(s)
    if 'controls' in sys.argv:
        print('broken models (each must fall short):')
        controls(s, chain)
    s.close()
    print('branches', dict(sorted(em.BRANCH.items())))


if __name__ == '__main__':
    main()
