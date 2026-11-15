#!/usr/bin/env python3
"""gate_creature.py: callcap differential gate of creature_model.step_tick against Archipelagos' $1a4e0.

From entry.snap (captured fresh from m2.snap at the first natural call of $1a4e0, A1 = $b000) it writes one REPL script
that, for each of N states, pokes the whole object block ($1db28 count, 32 phases, 32 positions), the player
bytes $1d696/$1d698 and sometimes a few map cells, then `callcap 1a4e0`s the routine (callcap restores the
state it started from, so the pokes persist and the next state overwrites them).  The model is handed only the
poked RAM; its predicted map ($3000..$12fff) and object block ($1db28..$1dbff) are compared byte for byte
with the poked RAM plus the callcap's changed bytes.  A state is a match when all of those bytes are equal.

usage: uv run python reversing/archipelagos/py/creature/gate_creature.py [N] [bug]    (bug: none|order|shift|lim5|nofoot|noclobber)
"""
import json, os, random, subprocess, sys
d = os.path.abspath(os.path.dirname(__file__))
here = d
while not os.path.exists(os.path.join(d, 'tools', 'rdis.py')):
    d = os.path.dirname(d)
ROOT = d
sys.path.insert(0, os.path.join(ROOT, 'tools'))
sys.path.insert(0, here)
from gfxview import load_ram
import creature_model as bm

WORK = os.path.join(ROOT, 'scratchpad', 'archipelagos', 'creature')
os.makedirs(WORK, exist_ok=True)
SNAP = bm.capture_entry()   # fresh capture every run
DLL = os.path.join(ROOT, 'bin', 'Debug', 'net8.0', 'M68000.dll')
N = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 80
BUG = next((a for a in sys.argv[1:] if a in ('order', 'shift', 'lim5', 'nofoot', 'noclobber')), None)
REGIONS = [(0x3000, 0x13000), (0x1DB28, 0x1DC00)]


def build():
    ram0, _ = load_ram(SNAP)
    cur = bytearray(ram0)
    rng = random.Random(58)
    land = [i for i in range(0x10000) if bm.ok(cur[0x3000 + i])]
    lines, states = [], []

    def poke_b(a, v):
        cur[a] = v & 0xFF
        lines.append('wb %x %02x' % (a, v & 0xFF))

    def poke_w(a, v):
        bm.ww(cur, a, v)
        lines.append('ww %x %04x' % (a, v & 0xFFFF))

    for si in range(N):
        n = 1 if si == 0 else rng.choice([1, 2, 3, 8, 16, 32])
        poke_w(0x1DB28, n)
        objs = []
        for i in range(32):
            if rng.random() < 0.6 or i < n and rng.random() < 0.5:
                ph = 0x14E
            else:
                ph = rng.randrange(0, 0x14E, 2)
            if si == 0 and i == 0:
                ph = 0x14E
            poke_w(0x1DB3E + 2 * i, ph)
            idx = rng.choice(land)
            # jitter to reach coasts, sea cells and the bit-7 cells beside the land
            idx = (idx + rng.choice([0, 0, 1, -1, 256, -256, 257, 3, -3, 768])) & 0xFFFF
            pos = (idx - 0x8000) & 0xFFFF
            poke_w(0x1DB3E + 64 + 2 * i, pos)
            objs.append(pos)
        p0 = objs[0]
        far = rng.choice([2, 6, 20, 60, 120])
        poke_b(0x1D698, ((p0 >> 8) + rng.randint(-far, far)) & 0xFF)
        poke_b(0x1D696, ((p0 & 0xFF) + rng.randint(-far, far)) & 0xFF)
        if rng.random() < 0.5:                       # map patches around some live objects
            for pos in objs[:min(n, 4)]:
                if rng.random() < 0.7:
                    mode = rng.choice(['rand', 'sea', 'rand'])
                    base = (0x3000 + ((pos + 0x8000) & 0xFFFF))
                    for dy in range(-2, 3):
                        for dx in range(-2, 3):
                            if rng.random() < 0.4:
                                a = base + dy * 256 + dx
                                if 0x3000 <= a < 0x13000:
                                    v = 0 if mode == 'sea' else rng.choice(
                                        [0, 1, 2, 3, 4, 5, 6, 7, 0x80, 0x81, 0x82, 0x83, 0x86, 0x87, 0x07, 0x06])
                                    poke_b(a, v)
        out = os.path.join(WORK, 'cb_%03d.json' % si)
        if os.path.exists(out) and not os.environ.get('KEEP'):
            os.remove(out)
        lines.append('callcap 1a4e0 200000 %s' % os.path.relpath(out, ROOT))
        pre = bytes(cur)
        states.append((si, out, pre))
    return lines, states


def parse_delta(path):
    j = json.load(open(path))
    return j


def main():
    lines, states = build()
    script = os.path.join(WORK, 'cb_script.txt')
    open(script, 'w').write('\n'.join(lines) + '\nq\n')
    log = os.path.join(WORK, 'cb_run.log')
    with open(script) as f, open(log, 'w') as lg:
        rc = subprocess.run(['dotnet', 'exec', DLL, 'resume', os.path.relpath(SNAP, ROOT), 'repl'], stdin=f,
                            stdout=lg, stderr=subprocess.STDOUT, cwd=ROOT).returncode
    txt = open(log).read()
    print('REPL rc', rc, ' callcap returned:', txt.count('callcap $01a4e0: returned'), 'of', len(states))
    match = bad = 0
    nev = ncell = 0
    outside = set()
    bm.BR.clear()
    for si, out, pre in states:
        if not os.path.exists(out):
            print('state', si, 'no callcap json'); bad += 1; continue
        j = parse_delta(out)
        emu = bytearray(pre)
        for a, old, new in j['mem']:
            if not any(lo <= a < hi for lo, hi in REGIONS):
                outside.add(a >> 8)
                continue
            assert pre[a] == old, (si, hex(a), pre[a], old)
            emu[a] = new
        mod = bytearray(pre)
        if BUG == 'nofoot':
            bm.footprint = lambda m, a, bug=None: None
            mod_bug = None
        else:
            mod_bug = BUG
        bm.step_tick(mod, mod_bug)
        # events this state: objects whose phase word was $14e
        nn = bm.rw(pre, 0x1DB28)
        ev = sum(1 for i in range(nn) if bm.rw(pre, 0x1DB3E + 2 * i) == 0x14E)
        diffs = [a for lo, hi in REGIONS for a in range(lo, hi) if emu[a] != mod[a]]
        changed = sum(1 for a in range(0x3000, 0x13000) if emu[a] != pre[a])
        nev += ev
        ncell += changed
        if os.environ.get('V'):
            print('state', si, 'n', nn, 'events', ev, 'changed', changed, 'diffs', len(diffs))
        if not diffs:
            match += 1
        else:
            bad += 1
            if bad <= 3:
                print('state', si, 'MISMATCH at', [hex(a) for a in diffs[:6]],
                      [(emu[a], mod[a]) for a in diffs[:6]])
    print('model==emulator %d/%d states (bug=%s); step events %d, map cells changed %d' % (match, len(states), BUG, nev, ncell))
    print('branch coverage:', dict(sorted(bm.BR.items())))
    print('delta addresses outside the compared regions (page numbers):', sorted(outside))


main()
