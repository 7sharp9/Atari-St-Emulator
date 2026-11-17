#!/usr/bin/env python3
"""captain_empty.py <out dir> [--rout DIR] [--postures 4,2,none] [--budget N]: can side 1 empty side 2's group 1 on
land 2 after the posture-4 field fight, with its lead `$041a` and the captain both alive (README "A second side-1
group")?

Three stages, each a loop.py replay with `--objs 1e5`:
  start   DIR/p4/in.jsonl (captain_rout.py's posture-4 arm: scripted o1 with posture 4 at the 190M field fight)
          replayed to 210M, where the fight is over, the lead walks home with prev mode `$3c` and his 14 followers
          wait ahead of him across a bay;
  march   from there two go to (`$02`) orders, at 0.4M to (24,64) and at 20M to (29,77), to 35M. The cells are the
          waypoints of `astar.py <start snap> 26 52 38 82 --cells`; an attack ordered from the Base walks straight
          at its target and stalls at the shore near (35,67) (README, same section);
  fight   captain_take.py from the march's end on the cell holding most followers (live men whose word 28 is the
          lead's offset), once per posture and once with no order (the control).
Then, per fight arm: what became of the men who were followers at the fight's start (still followers, routed = alive,
out of the group and with prev mode `$3c` in one of the 5 samples from leaving, dead = owner <= 0), the lead's samples in a candidate
mode with his follower count there, and the captain's lowest health. The arms differ only in the posture order."""
import json, struct, subprocess, sys, zlib
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = next(d for d in HERE.parents if (d / 'tools' / 'rdis.py').exists())
sys.path.insert(0, str(HERE))
from observe import load          # noqa: E402

OBJ, LEAD, CAP = 0x51b66, 0x041a, 0x1482
a = sys.argv[1:]
opt = lambda k, d: a[a.index(k) + 1] if k in a else d
out = Path(a[0]).resolve()
rout = ROOT / opt('--rout', 'scratchpad/cmd16/rout')
postures = opt('--postures', '4,2,none')
budget = opt('--budget', '60e6')
H = lambda R, o: struct.unpack_from('>H', R, o)[0]
sb = lambda v: v - 256 if v > 127 else v


def followers(R, base=0):
    return [k * 50 for k in range(512) if R[base + k * 50 + 6] == 0 and sb(R[base + k * 50 + 5]) > 0
            and H(R, base + k * 50 + 28) == LEAD]


def replay(d, rows, snap_at):
    d.mkdir(parents=True, exist_ok=True)
    for f in ('objs.bin', 'final.snap', 'decisions.jsonl', f'at_{snap_at}.snap'):
        (d / f).unlink(missing_ok=True)
    (d / 'in.jsonl').write_text(''.join(json.dumps(r) + '\n' for r in rows))
    rc = subprocess.run([sys.executable, str(HERE / 'loop.py'), str(d), '--replay', str(d / 'in.jsonl'), '--objs', '1e5',
                         '--snap-at', str(snap_at)], cwd=ROOT, stdout=open(d / 'loop.out', 'w'),
                        stderr=subprocess.STDOUT).returncode
    assert rc == 0, (d, rc)
    return d / f'at_{snap_at}.snap'


def samples(path):
    b = Path(path).read_bytes(); i = 0
    while i < len(b):
        step, n = struct.unpack_from('<QI', b, i); i += 12
        yield step, zlib.decompress(b[i:i + n]); i += n


rows = [json.loads(l) for l in (rout / 'p4' / 'in.jsonl').read_text().splitlines()]
s0 = replay(out / 'start', [dict(rows[0], budget=210000000)] + rows[1:], 210000000)
M = 35000000
rows = [dict(kind='start', snap=str(s0.relative_to(ROOT)), budget=M, every=5000000, gap=400000, side=1, take=True),
        dict(kind='applied', step=0, actions=[dict(side=1, take=True)]),
        dict(kind='applied', step=400000, actions=[dict(side=1, type=2, x=24, y=64, group=0)]),
        dict(kind='applied', step=20000000, actions=[dict(side=1, type=2, x=29, y=77, group=0)])]
rows += [dict(kind='decision', step=s) for s in range(0, M, 5000000)]
s1 = replay(out / 'march', rows, M)
R = load(s1)
cells = Counter((H(R, OBJ + o + 8) >> 8, H(R, OBJ + o + 10) >> 8) for o in followers(R, OBJ))
(x, y), n = cells.most_common(1)[0]
print(f'march end: captain at ({H(R, OBJ + CAP + 8) >> 8},{H(R, OBJ + CAP + 10) >> 8}), {sum(cells.values())} followers, '
      f'{n} on cell ({x},{y}); lead at ({H(R, OBJ + LEAD + 8) >> 8},{H(R, OBJ + LEAD + 10) >> 8})')
subprocess.run([sys.executable, str(HERE / 'captain_take.py'), str(out / 'fight'), str(s1), str(x), str(y),
                '--budget', budget, '--postures', postures], cwd=ROOT, check=True)
for p in postures.split(','):
    first = None; left = {}; seen = Counter(); hp = []; cand = Counter(); win = []
    for step, S in samples(out / 'fight' / f'p{p}' / 'objs.bin'):
        if first is None:
            first = followers(S)
        for o in first:
            if sb(S[o + 5]) <= 0:
                left[o] = 'dead'
            elif H(S, o + 28) != LEAD and left.get(o) != 'routed' and seen[o] < 5:
                seen[o] += 1
                left[o] = 'routed' if S[o + 30] == 0x3c else 'left, prev $%02x' % S[o + 30]
        hp.append(S[CAP + 45] if sb(S[CAP + 5]) > 0 else 0)
        if sb(S[LEAD + 5]) > 0 and S[LEAD + 31] in (0x8a, 0x3c):
            cand[len(followers(S))] += 1; win.append(step)
    fate = Counter(left.values()); fate['still followers'] = len(first) - len(left)
    print(f'posture {p}: the {len(first)} followers: {dict(fate)}; lead alive at end {sb(S[LEAD + 5]) > 0}, candidate-mode '
          f'samples by follower count {dict(cand)}' + (f' ({win[0] / 1e6:.1f}M..{win[-1] / 1e6:.1f}M)' if win else '') +
          f'; captain lowest health {min(hp)}, at end {hp[-1]}')
