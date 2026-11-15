#!/usr/bin/env python3
"""gate_creature_idle.py: creature_model.event_writes against a live `watch` log of the land map.

From entry.snap (m2.snap stopped at the first natural call of $1a4e0) it runs the game with `watch 3000 65536`:
  unpoked: no poke; `bpc 1a4e0 166` stops at the call whose phase word reaches $14e (the step tick), then 168
           more calls for the next one; 40M steps in all.
  poked  : (LABELLED POKES) before each of K natural calls of $1a4e0 the phase word $1db3e is set to $014e so
           that call steps and the position word $1db7e to a random land cell.
At each stepping call a snapshot is saved just before (bp at $1a4e0); the model is handed that RAM only and
its ordered writes (pc, cell, value) are compared with the watch lines whose PC is $1a634/$1a63e/$1a642/$1a6de
that follow, in order.  usage: uv run python reversing/archipelagos/py/creature/gate_creature_idle.py [K] [bug]
"""
import os, re, subprocess, sys
d = os.path.abspath(os.path.dirname(__file__)); here = d
while not os.path.exists(os.path.join(d, 'tools', 'rdis.py')):
    d = os.path.dirname(d)
ROOT = d
sys.path.insert(0, os.path.join(ROOT, 'tools')); sys.path.insert(0, here)
from gfxview import load_ram
import creature_model as bm
WORK = os.path.join(ROOT, 'scratchpad', 'archipelagos', 'creature')
os.makedirs(WORK, exist_ok=True); SNAP = bm.capture_entry()   # fresh capture every run
DLL = os.path.join(ROOT, 'bin', 'Debug', 'net8.0', 'M68000.dll')
K = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 40
BUG = next((a for a in sys.argv[1:] if a in ('order', 'shift', 'lim5', 'nofoot', 'noclobber')), None)
rel = lambda p: os.path.relpath(p, ROOT)
STEP_PCS = {0x1A634, 0x1A63E, 0x1A642, 0x1A6DE}


def run(name, script):
    sp = os.path.join(WORK, name + '.txt'); open(sp, 'w').write(script)
    with open(sp) as f, open(os.path.join(WORK, name + '.out'), 'w') as o, open(os.path.join(WORK, name + '.err'), 'w') as e:
        rc = subprocess.run(['dotnet', 'exec', DLL, 'resume', rel(SNAP), 'repl'], stdin=f, stdout=o, stderr=e, cwd=ROOT).returncode
    steps = []
    for ln in open(os.path.join(WORK, name + '.err')):
        m = re.match(r'WATCH: step=(\d+) pc=\$([0-9a-f]+) WriteByte \$([0-9a-f]+) <- \$([0-9a-f]+)', ln)
        if m and int(m.group(2), 16) in STEP_PCS:
            steps.append((int(m.group(1)), int(m.group(2), 16), int(m.group(3), 16), int(m.group(4), 16)))
    return rc, steps


def events(steps):
    ev, cur = [], []
    for s in steps:
        if cur and s[0] - cur[-1][0] > 2000:
            ev.append(cur); cur = []
        cur.append(s)
    if cur: ev.append(cur)
    return ev


def compare(tag, evs, pres):
    ok = 0
    for k, (ev, pre) in enumerate(zip(evs, pres)):
        ram, _ = load_ram(pre)
        exp = bm.event_writes(bytearray(ram), 0, BUG)
        got = [(s[1], s[2], s[3]) for s in ev]
        ok += exp == got
        if exp != got and k < 3:
            print('  mismatch event', k, '\n   model', [(hex(a), hex(b), hex(c)) for a, b, c in exp], '\n   emu  ', [(hex(a), hex(b), hex(c)) for a, b, c in got])
    cells = sorted({s[2] for ev in evs for s in ev})
    print('%s: %d events in the log, %d pre-snapshots, model==emulator %d/%d ordered 8-write sequences (bug=%s)' % (tag, len(evs), len(pres), ok, len(evs), BUG))
    return ok


# unpoked: two natural events
sc = 'watch 3000 65536\nbpc 1a4e0 166 40000000\nm 1db3e 2\nsnap %s\nbpc 1a4e0 168 40000000\nm 1db3e 2\nsnap %s\ns 400\nq\n' % (
    rel(os.path.join(WORK, 'un_pre0.snap')), rel(os.path.join(WORK, 'un_pre1.snap')))
# the second event's snapshot must be taken at the stepping call: bpc 168 from the first stop
rc, st = run('idle_unpoked', sc)
ev = events(st)
print('unpoked run: rc', rc, ' step-routine write events', len(ev), 'at steps', [e[0][0] for e in ev])
compare('unpoked', ev, [os.path.join(WORK, 'un_pre0.snap'), os.path.join(WORK, 'un_pre1.snap')])

# poked (labelled poke of $1db3e = $014e before K natural calls)
# the creature reaches the player after 5 steps and the routine then stops being called (the bp below never
# hits), so each call also gets the creature's position poked to another land cell (the second labelled poke)
ram0, _ = load_ram(SNAP)
land = [i for i in range(0x10000) if (ram0[0x3000 + i] & 7) >= 5 and not ram0[0x3000 + i] & 0x80]
import random
rng = random.Random(7)
poss = [(rng.choice(land) - 0x8000) & 0xFFFF for _ in range(K)]
def poke(k):
    return ['ww 1db3e 014e', 'ww 1db7e %04x' % poss[k]]
lines = ['watch 3000 65536'] + poke(0) + ['snap %s' % rel(os.path.join(WORK, 'pk_pre_000.snap')), 's 400']
for k in range(1, K):
    lines += ['bp 1a4e0 300000'] + poke(k) + ['snap %s' % rel(os.path.join(WORK, 'pk_pre_%03d.snap' % k)), 's 400']
lines += ['q']
rc, st = run('idle_poked', '\n'.join(lines) + '\n')
ev = events(st)
print('poked run: rc', rc, ' events', len(ev))
compare('poked', ev, [os.path.join(WORK, 'pk_pre_%03d.snap' % k) for k in range(K)])
