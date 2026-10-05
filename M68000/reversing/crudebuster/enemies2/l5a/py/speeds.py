"""Per-state movement of a pool A type from a drive5.lua log: mean |dx| and dy per frame between consecutive frames in the same state (rows with the same slot episode),
the x velocity field (+22, signed 16.16 long) seen, and the largest vertical excursion within a run (jump height).
usage: speeds.py <log> <type hex> [<log> ...]"""
import sys, os, collections
sys.path.insert(0, os.path.dirname(__file__))
from loglib import load, u16, runs
ty = int(sys.argv[2], 16)
agg = collections.defaultdict(lambda: dict(n=0, adx=0, ady=0, v=collections.Counter(), jh=0, runs=0, len=[]))
for log in [sys.argv[1]] + sys.argv[3:]:
    F, eps = load(log)
    for ep in eps:
        if ep.type != ty: continue
        for st, a, z, n, b0, b1 in runs(ep):
            rows = [b for f, b in ep.rows if a <= f <= z]
            A = agg[st]; A['runs'] += 1; A['len'].append(n)
            for r0, r1 in zip(rows, rows[1:]):
                dx = abs(u16(r1, 8) - u16(r0, 8)); dy = u16(r1, 12) - u16(r0, 12)
                if dx > 100: continue  # wraps
                A['n'] += 1; A['adx'] += dx; A['ady'] += abs(dy if abs(dy) < 100 else 0)
            for r in rows: A['v'][int.from_bytes(r[22:26], 'big', signed=True)] += 1
            ys = [u16(r, 12) for r in rows]
            if ys: A['jh'] = max(A['jh'], max(ys) - min(ys))
print("state: runs  frames-per-run(min..max)  mean|dx|/frame  mean|dy|/frame  max y excursion  most common +22 (px/frame = value/65536)")
for st in sorted(agg):
    A = agg[st]
    if A['n'] == 0: continue
    mv = ", ".join(f"{v/65536:.3f}x{c}" for v, c in A['v'].most_common(3))
    print(f"  {st:02x}: {A['runs']:3d} runs {min(A['len'])}..{max(A['len'])}  dx {A['adx']/A['n']:.3f}  dy {A['ady']/A['n']:.3f}  ymax-ymin {A['jh']}  v22 {mv}")
