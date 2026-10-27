"""Gate for the enemy army tick model (ai.md section 2): runs the game's own `$c136` N times in a row in `stserver`
and checks army_model.tick against every tick.

usage: gate_army.py [ticks] [start.snap]
Needs $MIDWINTER_WORK (default <root>/scratchpad/midwinter) holding d_options.snap, d_team.snap, d_stark.snap and
zuul067.st (indexed in
scratchpad/ANCHORS.md). Labelled poke: each tick is a call of `$c136` from a planted return address ($800, the
program entry, used only as a stop address), A6 = $2c376, interrupts masked. Compares, per tick, the unit table, the
node states, the feature list's kind bytes, the RNG seed and the scratch/flag words. Also models the hourly supply
updates `$f56e`/`$f5e2`: the natural ones of the PLAY head start (d_options.snap, the click made through the REPL),
and in the chained run one pair after every seventh tick, as `$ee30` orders them. Expected (ai.md): natural ticks
42/42, natural supply 10/10, unchanged between calls 31008/31008; after one situation report (d_team.snap, the
clock icon and the report's icon) 9/9 and 4864/4864; chained ticks 1000/1000, chained supply 284/284.
"""
import json, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
root = os.environ.get('M68000_ROOT') or HERE
while not os.path.exists(os.path.join(root, 'tools', 'rdis.py')):
    root = os.path.dirname(root)
WORK = os.environ.get('MIDWINTER_WORK') or os.path.join(root, 'scratchpad', 'midwinter')
SERVER = os.path.join(root, 'server', 'bin', 'Debug', 'net8.0', 'stserver.dll')
DLL = os.path.join(root, 'bin', 'Debug', 'net8.0', 'M68000.dll')
DISK = os.path.join(WORK, 'zuul067.st')
OUT = os.path.join(WORK, 'army', 'gate')
sys.path.insert(0, HERE)
import army_model as am  # noqa: E402

# regions the tick may write; the feature list is the 96 records from $2a150
REGIONS = [(am.UNITS, 512), (am.STATE, 96), (am.SEED, 2), (0x2bae4, 4), (0x2bb2e, 4), (0x2a150, 0x2a8a0 - 0x2a150)]
RET = 0x800


class Server:
    def __init__(self):
        self.p = subprocess.Popen(['dotnet', 'exec', SERVER], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                  text=True, cwd=root)
        self.seq = 0

    def __call__(self, method, **params):
        self.seq += 1
        self.p.stdin.write(json.dumps({'jsonrpc': '2.0', 'id': self.seq, 'method': method, 'params': params}) + '\n')
        self.p.stdin.flush()
        r = json.loads(self.p.stdout.readline())
        if 'error' in r:
            sys.exit(f'{method}: {r["error"]["message"]}')
        return r['result']

    def read(self, a, n):
        return bytes.fromhex(self('read', addr=a, len=n))

    def close(self):
        self.p.stdin.close()
        self.p.wait()


def snapshot_mem(s):
    m = am.Mem(bytes(0x30000))
    for a, n in REGIONS + [(am.NODES, 384), (am.ADJ, 384), (am.MULT, 2)]:
        m.b[a:a + n] = s.read(a, n)
    return m


class Score:
    def __init__(self):
        self.ticks = self.ok_ticks = self.ok_bytes = self.total = self.arrive = self.choose = self.changed = 0

    def check(self, s, pre, label, step=am.tick):
        """Model one tick from `pre`, compare with the machine `s` after the game's tick."""
        model = am.Mem(pre.b)
        before = [model.u8(am.UNITS + 16 * u + 13) for u in range(32)]
        step(model)
        after = [model.u8(am.UNITS + 16 * u + 13) for u in range(32)]
        self.arrive += sum(1 for b, a in zip(before, after) if 0 < b < 0x80 and a == 0)
        self.choose += sum(1 for b, a in zip(before, after) if b == 0 and a != 0)
        good = True
        for a, ln in REGIONS:
            got = s.read(a, ln)
            exp = bytes(model.b[a:a + ln])
            same = sum(1 for x, y in zip(got, exp) if x == y)
            self.changed += sum(1 for x, y in zip(got, pre.b[a:a + ln]) if x != y)
            self.ok_bytes += same
            self.total += ln
            if same != ln:
                if good:
                    d = [(hex(a + j), exp[j], got[j]) for j in range(ln) if exp[j] != got[j]][:12]
                    print(f'{label} mismatch (addr, model, game): {d}')
                good = False
        self.ticks += 1
        self.ok_ticks += good

    def report(self, name):
        print(f'{name}: ticks {self.ok_ticks}/{self.ticks}, bytes {self.ok_bytes}/{self.total}, '
              f'arrivals {self.arrive}, new targets {self.choose}, game bytes changed {self.changed}')


PLAY = ('PLAY head start', 'd_options.snap', 42,
        ['mouse move 80 0', 's 100000', 'mouse move 80 80', 's 100000', 'mouse move 0 75', 's 2000000'])
# The Team's clock icon (288,32: `$ec8c`) gives the situation report `$ef36`; its icon (0,168) runs the nine ticks
REPORT = ('situation report', 'd_team.snap', 9,
          ['mouse move 70 -55', 's 100000', 'mouse move 70 -55', 's 2000000', 'mouse down l', 's 300000',
           'mouse up l', 's 100000000', 'mouse move -127 127', 's 100000', 'mouse move -127 12', 's 100000',
           'mouse move -30 0', 's 2000000'])


def natural(s, leg):
    """The natural calls of $c136 (and the supply updates between them) after a click made through the REPL; also
    counts the army bytes changed between one call's return and the next call's entry (other code touching the army)."""
    name, start, nticks, moves = leg
    # the click goes through the REPL (the stserver mouse path did not register this game's click: handoff trap)
    snap0 = os.path.join(OUT, start.replace('.snap', '_c136_0.snap'))
    lines = moves + ['mouse down l', 'u c136 3000000', f'snap {snap0}', 'q']
    p = subprocess.run(['dotnet', 'exec', DLL, 'resume', os.path.join(WORK, start), 'repl', '--disk-a', DISK],
                       input='\n'.join(lines) + '\n', capture_output=True, text=True, cwd=root,
                       env=dict(os.environ, ATARI_NOTRACE='1'))
    if 'state saved' not in p.stdout or 'reached' not in p.stdout:
        sys.exit(f'REPL run to the first $c136 failed:\n{p.stdout[-2000:]}{p.stderr[-2000:]}')
    s('load', snapshot=snap0, disk=DISK)
    sc, sup, between, compared, last, ticks, first = Score(), Score(), 0, 0, None, 0, True
    stops = [0xc136, 0xf56e, 0xf5e2]
    while ticks < nticks:
        r = {'reason': 'until'} if first else s('run', max_steps=3000000, until_pc=stops)
        first = False
        if r['reason'] != 'until':
            sys.exit(f'natural run: stopped after {ticks} ticks ({r})')
        pc = int(s('regs')['pc'].lstrip('$'), 16)
        pre = snapshot_mem(s)
        if last is not None:
            between += sum(1 for a, ln in REGIONS[:2] for j in range(ln) if pre.b[a + j] != last.b[a + j])
            compared += sum(ln for _, ln in REGIONS[:2])
        ret = int.from_bytes(s.read(int(s('regs')['a7'].lstrip('$'), 16), 4), 'big')
        r = s('run', max_steps=400000, until_pc=ret)
        if r['reason'] != 'until':
            sys.exit(f'natural call at ${pc:x}: no return to ${ret:x} ({r})')
        if pc == 0xc136:
            sc.check(s, pre, f'natural tick {ticks}')
            ticks += 1
        else:
            sup.check(s, pre, f'supply ${pc:x}', step=lambda m, f=(11 if pc == 0xf56e else 12): am.supply(m, f))
        last = snapshot_mem(s)
    sc.report(f'natural ticks ({name})')
    if sup.ticks:
        sup.report(f'natural supply updates ({name})')
    print(f'army/node-state bytes unchanged between the calls (no other writer): {compared - between}/{compared}')


def chained(s, n, start):
    """n back-to-back calls of $c136 from `start`, each from a planted return address."""
    s('load', snapshot=start, disk=DISK)
    sp = int(str(s('regs')['a7']).lstrip('$'), 16) - 64
    sc, sup = Score(), Score()

    def call(entry):
        s('poke', addr=sp, width=4, value=RET)
        s('set_reg', name='a7', value=sp)
        s('set_reg', name='a6', value=0x2c376)
        s('set_reg', name='sr', value=0x2700)
        s('set_reg', name='pc', value=entry)
        r = s('run', max_steps=400000, until_pc=RET)
        if r['reason'] != 'until':
            sys.exit(f'${entry:x} did not return ({r})')

    for i in range(n):
        pre = snapshot_mem(s)
        call(0xc136)
        sc.check(s, pre, f'chained tick {i}')
        if i % 7 == 6:  # the game's hourly order: seven ticks, then $f56e and $f5e2 ($ee30)
            for entry, field in ((0xf56e, 11), (0xf5e2, 12)):
                pre = snapshot_mem(s)
                call(entry)
                sup.check(s, pre, f'chained supply ${entry:x}', step=lambda m, f=field: am.supply(m, f))
    sc.report(f'chained ticks from {os.path.basename(start)}')
    sup.report('chained supply updates')


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 1000
    start = sys.argv[2] if len(sys.argv) > 2 else os.path.join(WORK, 'd_stark.snap')
    os.makedirs(OUT, exist_ok=True)
    s = Server()
    natural(s, PLAY)
    natural(s, REPORT)
    chained(s, n, start)
    s.close()
    print('branches', dict(sorted(am.BRANCH.items())))


if __name__ == '__main__':
    main()
