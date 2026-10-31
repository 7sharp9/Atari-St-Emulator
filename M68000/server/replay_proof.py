"""replay_to proof (DEVELOPING.md, "Record and replay"): a replayed machine is byte-identical to the recorded run.

    python3 server/replay_proof.py <stserver.dll> <pre_pick.snap> <powermonger.st> <outdir>

From PowerMonger's `commander/leadkill` `pre_pick.snap` (base step B), record 2.6M steps with a checkpoint every
500,000 and three journalled inputs: a mouse move at B+1,000,000 (a checkpoint step, so the checkpoint there holds
it), the `r39` poke `w 521cc 04000000` at B+1,234,567 and an IKBD byte pair at B+2,100,001 (both mid-interval, so the
replay must re-apply them). The recording run saves a snapshot at 12 steps S: on and next to checkpoints, at and just
after each input, and the end. Then, in a shuffled order, `replay_to S` and `save` for each, and every pair must be
byte-identical. Falsifier: any byte differs. Controls: a run without the inputs differs from the recorded one at
B+1,234,568 (the poke is visible, so an identity is not vacuous), and the 12 recorded snapshots are pairwise distinct.
Exit status 0 = all pass.
"""
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tools'))
from stclient import StServer  # noqa: E402

dll, snap, disk, out = sys.argv[1:5]
os.makedirs(out, exist_ok=True)
s = StServer(os.getcwd(), dll=dll)
B = s('load', snapshot=snap, disk=disk)['step']
inputs = {B + 1_000_000: ('mouse', dict(action='move', dx=3, dy=-2)),
          B + 1_234_567: ('poke', dict(addr=0x521cc, width=4, value=0x04000000)),
          B + 2_100_001: ('kbd', dict(bytes=[0x39, 0xb9]))}
points = [B + d for d in (1, 137_000, 499_999, 500_000, 760_001, 1_000_000, 1_234_567, 1_234_568,
                          1_700_000, 2_100_001, 2_599_999, 2_600_000)]
fails = []


def check(name, cond, detail=''):
    print(('PASS ' if cond else 'FAIL ') + name + (f'  {detail}' if detail else ''))
    if not cond:
        fails.append(name)


def goto(target):
    n = target - s('regs')['step']
    if n > 0:
        r = s('step', n=n)
        assert 'error' not in r, r


s('record_start', every=500_000)
for t in sorted(set(points) | set(inputs)):
    goto(t)
    if t in inputs:
        m, p = inputs[t]
        s(m, **p)
    if t in points:
        s('save', path=f'{out}/rec_{t}.snap')
r = s('record_stop')
print(f"recorded {r['base']}..{r['end']}: {r['checkpoints']} checkpoints, {r['inputs']} inputs")
check('recording shape', r['checkpoints'] == 6 and r['inputs'] == 3, f"{r['checkpoints']} checkpoints, {r['inputs']} inputs")

order = points[:]
random.Random(39).shuffle(order)
same = 0
for t in order:
    rr = s('replay_to', step=t)
    s('save', path=f'{out}/rep_{t}.snap')
    a = open(f'{out}/rec_{t}.snap', 'rb').read()
    b = open(f'{out}/rep_{t}.snap', 'rb').read()
    if a == b:
        same += 1
    else:
        d = next(i for i in range(min(len(a), len(b))) if a[i] != b[i]) if len(a) == len(b) else -1
        print(f'  step {t} (from checkpoint {rr["from_checkpoint"]}): first differing byte {d}')
check('replay_to byte-identical', same == len(points), f'{same}/{len(points)}')

s('load', snapshot=snap, disk=disk)
goto(B + 1_234_568)
s('save', path=f'{out}/plain_{B + 1_234_568}.snap')
check('control: the inputs are visible',
      open(f'{out}/plain_{B + 1_234_568}.snap', 'rb').read() != open(f'{out}/rec_{B + 1_234_568}.snap', 'rb').read())
blobs = [open(f'{out}/rec_{t}.snap', 'rb').read() for t in points]
check('control: recorded snapshots pairwise distinct', len(set(blobs)) == len(blobs), f'{len(set(blobs))}/{len(blobs)}')
s.close()
sys.exit(1 if fails else 0)
