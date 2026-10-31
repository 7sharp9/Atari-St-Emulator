"""first_divergence proof (DEVELOPING.md, "Record and replay"): it finds a journalled poke's step and bytes, and no
divergence between identical runs.

    python3 server/divergence_proof.py <stserver.dll> <pre_pick.snap> <powermonger.st> <outdir>

From PowerMonger's `commander/leadkill` `pre_pick.snap`, four recordings of 2.6M steps (a checkpoint every 500,000):
A plain, C plain again, B with the `r39` poke `w 521cc 04000000` journalled 1,000,000 steps in (a checkpoint step),
D with the same poke at 1,234,567 (mid-interval, so the step comes from the binary search, not a checkpoint).
Expected: A/B and A/D diverge at the poke's step with the first differing bytes in $521cc..$521cf; A/C and C/A do not
diverge. Falsifier: an earlier divergence (a determinism hole), a later one, other bytes, or none.
Exit status 0 = all pass.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tools'))
from stclient import StServer  # noqa: E402

dll, snap, disk, out = sys.argv[1:5]
N = 2_600_000
s = StServer(os.getcwd(), dll=dll)
fails = []


def check(name, cond, detail=''):
    print(('PASS ' if cond else 'FAIL ') + name + (f'  {detail}' if detail else ''))
    if not cond:
        fails.append(name)


def record(poke_at=None):
    base = s('load', snapshot=snap, disk=disk)['step']
    s('record_start', every=500_000)
    if poke_at is not None:
        s('step', n=poke_at)
        s('poke', addr=0x521cc, width=4, value=0x04000000)
        s('step', n=N - poke_at)
    else:
        s('step', n=N)
    return base, s('record_stop')['id']


B0, A = record()
_, C = record()
_, Bp = record(1_000_000)
_, Dp = record(1_234_567)
for name, x, y, at in (('A/B', A, Bp, 1_000_000), ('A/D', A, Dp, 1_234_567), ('A/C', A, C, None), ('C/A', C, A, None)):
    d = s('first_divergence', a=x, b=y)['divergence']
    if at is None:
        check(f'{name} no divergence', d is None, str(d))
        continue
    want = B0 + at
    first = int(d['bytes'][0]['addr'][1:], 16) if d and d['bytes'] else None
    check(f'{name} diverges at the poke step {want}', d is not None and d['step'] == want, str(d and d['step']))
    check(f'{name} first differing byte in $521cc..$521cf', first is not None and 0x521cc <= first <= 0x521cf,
          str(d and d['bytes'][:4]))
    check(f'{name} journal bound at the poke step', d is not None and d['journal_step'] == want, str(d and d['journal_step']))
s.close()
sys.exit(1 if fails else 0)
