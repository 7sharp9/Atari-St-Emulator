"""Hop 3 of the Amazon (room 188..285 to the block-283 exit into 299..318) on real input with no health pokes, in one recorded file.

    cd M68000 && ATARI_NOTRACE=1 uv run python reversing/impossamole/py/route/unpoked_hop3.py [--force] [--nproc N]

Stages (each skipped when its end snapshot already exists, unless --force; output under scratchpad/impossamole/agents/unpoked/):
  1. `policy.py run BEST 1-5 --chain`: segments 1-5 under the BEST guard (bee rule, monkey snipe and lure-and-kill, hop over immune ones);
  2. `auto_pits.py`: the four water pits, rollout search over the take-off delay so the hero lands on a crocodile whose jaws are shut;
  3. `segsweep.py seg7_pillars` (start-delay search), `wait_opt.py` for segments 8-10 (greedy wait points), `segsweep.py seg11_shaft_exit`;
  4. concatenate every stage's .repl into `hop3_unpoked.repl`, replay it in ONE process from `pass103/room188.snap` and `cmp` the snapshot against
     the live stage-3 end snapshot (expect IDENTICAL), then print health and block.
`room188.snap` already holds health 12 12 03 00 at `$bb74`, so the initial `w bb74 12120300` that `policy.py` writes changes no byte.
Searching is the slow part (about 1 to 1.5 hours on 6 cores); the replay is about a minute.
"""
import os, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
BASE = 'scratchpad/impossamole/agents/unpoked'
DISK = 'scratchpad/impossamole/impossamole cr replicants - emotion cr replicants.st'
START = 'scratchpad/impossamole/pass103/room188.snap'
PY = sys.executable
force = '--force' in sys.argv
nproc = sys.argv[sys.argv.index('--nproc') + 1] if '--nproc' in sys.argv else '6'
env = dict(os.environ, ATARI_NOTRACE='1')


def sh(args, log):
    print('$', ' '.join(args), '>', log, flush=True)
    with open(os.path.join(ROOT, log), 'w') as f:
        r = subprocess.run(args, cwd=ROOT, env=env, stdout=f, stderr=subprocess.STDOUT)
    if r.returncode:
        sys.exit(f'failed: {args} (see {log})')


def stage(snap, args, log):
    if not force and os.path.exists(os.path.join(ROOT, snap)):
        print('skip (exists):', snap, flush=True)
        return
    os.makedirs(os.path.join(ROOT, os.path.dirname(log)), exist_ok=True)
    sh(args, log)
    if not os.path.exists(os.path.join(ROOT, snap)):
        sys.exit(f'stage produced no {snap}, see {log}')


R = 'reversing/impossamole/py/route'
os.makedirs(os.path.join(ROOT, BASE), exist_ok=True)
seg5 = f'{BASE}/policy/BEST_chain/seg5.snap'
stage(seg5, [PY, f'{R}/policy.py', 'run', 'BEST', '1-5', '--chain'], f'{BASE}/stage1.out')
stage(f'{BASE}/pits/pit4.snap', [PY, f'{R}/auto_pits.py', seg5, f'{BASE}/pits', nproc], f'{BASE}/stage2.out')
prev = f'{BASE}/pits/pit4.snap'
stage(f'{BASE}/s7/seg7_pillars.snap', [PY, f'{R}/segsweep.py', 'seg7_pillars', prev, f'{BASE}/s7', nproc], f'{BASE}/stage3_seg7.out')
prev = f'{BASE}/s7/seg7_pillars.snap'
pieces = [f'{BASE}/policy/BEST_chain/seg{k}.repl' for k in range(1, 6)] + [f'{BASE}/pits/pit{k}.repl' for k in range(1, 5)] + [f'{BASE}/s7/seg7_pillars.repl']
for seg in ('seg8_stairs_roof', 'seg9_ladder_corridor', 'seg10_bead_ladder'):
    stage(f'{BASE}/{seg}/{seg}.snap', [PY, f'{R}/wait_opt.py', seg, prev, f'{BASE}/{seg}', nproc], f'{BASE}/stage3_{seg}.out')
    prev = f'{BASE}/{seg}/{seg}.snap'
    pieces.append(f'{BASE}/{seg}/{seg}.repl')
stage(f'{BASE}/s11/seg11_shaft_exit.snap', [PY, f'{R}/segsweep.py', 'seg11_shaft_exit', prev, f'{BASE}/s11', nproc, '0', '60', '30'], f'{BASE}/stage3_seg11.out')
pieces.append(f'{BASE}/s11/seg11_shaft_exit.repl')
live = f'{BASE}/s11/seg11_shaft_exit.snap'

lines = []
for p in pieces:
    body = [l.rstrip('\n') for l in open(os.path.join(ROOT, p))]
    lines += [l for l in body if not l.startswith('snap ') and l != 'q']
out = os.path.join(ROOT, BASE, 'hop3_unpoked_replayed.snap')
lines += [f'snap {out}', 'q']
repl = os.path.join(ROOT, BASE, 'hop3_unpoked.repl')
open(repl, 'w').write('\n'.join(lines) + '\n')
print(len(lines), 'commands ->', repl, flush=True)
with open(repl) as fin, open(os.path.join(ROOT, BASE, 'replay.out'), 'w') as fout:
    subprocess.run(['dotnet', 'exec', 'bin/Debug/net8.0/M68000.dll', 'resume', START, 'repl', '--disk-a', DISK], cwd=ROOT, env=env, stdin=fin, stdout=fout, stderr=subprocess.STDOUT)
same = open(out, 'rb').read() == open(os.path.join(ROOT, live), 'rb').read()
print('replayed snapshot vs live stage-3 end:', 'IDENTICAL' if same else 'DIFFERENT')
sys.path.insert(0, os.path.join(ROOT, 'tools'))
from pathlib import Path
from pm_export import ram_from_snap
ram = ram_from_snap(Path(out))
print('health $bb74..77:', ram[0xbb74:0xbb78].hex(), ' left block $227b4:', int.from_bytes(ram[0x227b4:0x227b6], 'big'))
sys.exit(0 if same else 1)
