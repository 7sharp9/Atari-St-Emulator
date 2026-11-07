"""Recording-on-disk proof (DEVELOPING.md, "Record and replay"): a recording written with record_start's 'dir' and
read back by record_load in another process replays byte-identical to the recorded run, and first_divergence works
across recordings made in different processes.

    python3 server/record_disk_proof.py <stserver.dll> <pre_pick.snap> <powermonger.st> <outdir>

From PowerMonger's `commander/leadkill` `pre_pick.snap` (base step B), process 1 records 2.6M steps into
<outdir>/recA with a checkpoint every 500,000 and keep=2, so four of the six checkpoints leave memory and live only
in their files, and journals the three inputs replay_proof.py uses (a mouse move on the checkpoint step B+1,000,000,
the `r39` poke `w 521cc 04000000` at B+1,234,567 and an IKBD pair at B+2,100,001). It saves the recording run at 12
steps S, then replays each in a shuffled order in the same process (file restores of the evicted checkpoints): 12
of 12 byte-identical. Process 2 starts fresh, record_load's recA and replays the 12 again: 12 of 12. Process 3
records the same run without the poke into recB; process 4 loads recA and recB and first_divergence must give the
poke's step B+1,234,567 with the first differing byte in $521cc..$521cf, as divergence_proof.py does in memory.
Falsifiers: any byte differs; another divergence step. Controls: recA_bad, a copy with one RAM byte flipped in
ck_<B+1,500,000>.snap, replays the point B+1,700,000 differently (so the replays read the files) and the points before
B+1,500,000 identically; a run that wrote no inputs differs at B+1,234,568 (replay_proof's control, here from the
loaded recording's base). Exit status 0 = all pass.
"""
import os
import random
import shutil
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tools'))
from stclient import StServer  # noqa: E402

dll, snap, disk, out = sys.argv[1:5]
out = os.path.abspath(out)
os.makedirs(out, exist_ok=True)
for d in ('recA', 'recB', 'recA_bad'):
    shutil.rmtree(f'{out}/{d}', ignore_errors=True)
fails = []


def check(name, cond, detail=''):
    print(('PASS ' if cond else 'FAIL ') + name + (f'  {detail}' if detail else ''))
    if not cond:
        fails.append(name)


def server():
    return StServer(os.getcwd(), dll=dll)


def goto(s, target):
    n = target - s('regs')['step']
    if n > 0:
        r = s('step', n=n)
        assert 'error' not in r, r


def record(s, d, inputs, points, tag):
    s('record_start', every=500_000, dir=d, keep=2)
    for t in sorted(set(points) | set(inputs)):
        goto(s, t)
        if t in inputs:
            m, p = inputs[t]
            s(m, **p)
        if t in points:
            s('save', path=f'{out}/{tag}_{t}.snap')
    return s('record_stop')


def replay_all(s, tag, order):
    same, diff = 0, []
    for t in order:
        rr = s('replay_to', step=t)
        assert 'error' not in rr, rr
        s('save', path=f'{out}/{tag}_{t}.snap')
        if open(f'{out}/rec_{t}.snap', 'rb').read() == open(f'{out}/{tag}_{t}.snap', 'rb').read():
            same += 1
        else:
            diff.append(t)
    return same, diff


s = server()
B = s('load', snapshot=snap, disk=disk)['step']
inputs = {B + 1_000_000: ('mouse', dict(action='move', dx=3, dy=-2)),
          B + 1_234_567: ('poke', dict(addr=0x521cc, width=4, value=0x04000000)),
          B + 2_100_001: ('kbd', dict(bytes=[0x39, 0xb9]))}
points = [B + d for d in (1, 137_000, 499_999, 500_000, 760_001, 1_000_000, 1_234_567, 1_234_568,
                          1_700_000, 2_100_001, 2_599_999, 2_600_000)]
order = points[:]
random.Random(39).shuffle(order)

r = record(s, f'{out}/recA', inputs, points, 'rec')
print(f"recorded {r['base']}..{r['end']}: {r['checkpoints']} checkpoints, {r['inputs']} inputs, dir {r['dir']}")
cks = sorted(f for f in os.listdir(f'{out}/recA') if f.endswith('.snap'))
check('recording shape', r['checkpoints'] == 6 and r['inputs'] == 3 and not r['disk_written'],
      f"{r['checkpoints']} checkpoints, {r['inputs']} inputs, disk_written {r['disk_written']}")
check('six checkpoint files plus journal and manifest',
      len(cks) == 6 and os.path.exists(f'{out}/recA/journal.jsonl') and os.path.exists(f'{out}/recA/recording.json'),
      ' '.join(cks))
same, diff = replay_all(s, 'rep1', order)
check('process 1 (four checkpoints evicted to file) replay_to byte-identical', same == len(points),
      f'{same}/{len(points)} {diff}')
s.close()

s = server()
lr = s('record_load', dir=f'{out}/recA')
check('record_load shape', lr.get('checkpoints') == 6 and lr.get('inputs') == 3 and lr.get('step') == B, str(lr))
same, diff = replay_all(s, 'rep2', order)
check('process 2 (record_load) replay_to byte-identical', same == len(points), f'{same}/{len(points)} {diff}')
s('replay_to', step=B)
goto(s, B + 1_234_568)
s('save', path=f'{out}/plain_{B + 1_234_568}.snap')
check('control: the inputs are visible',
      open(f'{out}/plain_{B + 1_234_568}.snap', 'rb').read() != open(f'{out}/rec_{B + 1_234_568}.snap', 'rb').read())
s.close()

# Corrupt one RAM byte of the checkpoint at B+1,500,000 in a copy: RAM starts after "A68S", the version byte, 19
# int32 registers, the int16 CCR and the RAM array's int32 length (SaveState).
shutil.copytree(f'{out}/recA', f'{out}/recA_bad')
bad = f'{out}/recA_bad/ck_{B + 1_500_000}.snap'
blob = bytearray(open(bad, 'rb').read())
off = 4 + 1 + 19 * 4 + 2 + 4 + 0x521cc
blob[off] ^= 0xff
open(bad, 'wb').write(blob)
os.remove(bad + '.prov.json')  # it records the unflipped file's hash
s = server()
s('record_load', dir=f'{out}/recA_bad', disk=disk)
before = [t for t in points if t < B + 1_500_000]
same, diff = replay_all(s, 'bad', before + [B + 1_700_000])
check('control: a corrupted checkpoint file changes only the replays from it',
      diff == [B + 1_700_000] and same == len(before), f'differ at {diff}, {same}/{len(before)} before it identical')
s.close()

s = server()
s('load', snapshot=snap, disk=disk)
nopoke = {k: v for k, v in inputs.items() if v[0] != 'poke'}
record(s, f'{out}/recB', nopoke, [], 'recB')
s.close()

s = server()
a = s('record_load', dir=f'{out}/recA')['id']
b = s('record_load', dir=f'{out}/recB')['id']
d = s('first_divergence', a=a, b=b)['divergence']
want = B + 1_234_567
first = int(d['bytes'][0]['addr'][1:], 16) if d and d['bytes'] else None
check(f'recordings from two processes diverge at the poke step {want}', d is not None and d['step'] == want,
      str(d and d['step']))
check('first differing byte in $521cc..$521cf', first is not None and 0x521cc <= first <= 0x521cf,
      str(d and d['bytes'][:4]))
s.close()
sys.exit(1 if fails else 0)
