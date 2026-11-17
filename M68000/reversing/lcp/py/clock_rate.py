"""Measure the game clock against the machine's clocks on a natural run (README, "Needs and the clock"): runs
house.snap in chunks under `stserver` `hits` and records per chunk the frame counter `$51424`, the game second /
minute / hour words, `_hz_200` (`$4ba`), the VBL count `_vbclock` (`$462`) and the arrivals at `$24648` (tick
entry), `$2465c` (a second counted) and `$24670` (a minute body). Writes a CSV to $LCP_WORK/clock/.

usage: clock_rate.py [chunks] [steps_per_chunk]
"""
import csv, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
root = os.environ.get('M68000_ROOT') or HERE
while not os.path.exists(os.path.join(root, 'tools', 'rdis.py')):
    root = os.path.dirname(root)
WORK = os.environ.get('LCP_WORK') or os.path.join(root, 'scratchpad', 'lcp')
sys.path.insert(0, os.path.join(root, 'tools'))
from stclient import StServer  # noqa: E402

CH = int(sys.argv[1]) if len(sys.argv) > 1 else 60
STEPS = int(sys.argv[2]) if len(sys.argv) > 2 else 1000000
ADDRS = [0x24648, 0x2465c, 0x24670]
s = StServer(root)
s('load', snapshot=os.path.join(WORK, 'house.snap'), disk=os.path.join(WORK, 'disk', 'tmbird03_even.st'))
rd = lambda a, n: int.from_bytes(s.read(a, n), 'big')


def sample():
    return {'frame': rd(0x51424, 2), 'sec': rd(0x4c592, 2), 'min': rd(0x55102, 2), 'hour': rd(0x4ca20, 2),
            'hz200': rd(0x4ba, 4), 'vbl': rd(0x462, 4), 'thirst': rd(0x51464, 2), 'hunger': rd(0x5146a, 2),
            'pee': rd(0x51470, 2), 'ill': rd(0x5145a, 2), 'mood': rd(0x5144e, 2)}


rows = [dict(chunk=0, steps=0, tick=0, secs=0, mins=0, **sample())]
for c in range(1, CH + 1):
    h = s('hits', steps=STEPS, addrs=ADDRS)
    cnt = {int(e['addr'].lstrip('$'), 16): e['count'] for e in h['hits']}
    rows.append(dict(chunk=c, steps=c * STEPS, tick=cnt.get(0x24648, 0), secs=cnt.get(0x2465c, 0),
                     mins=cnt.get(0x24670, 0), **sample()))
s.close()
out = os.path.join(WORK, 'clock', f'clock_{CH}x{STEPS}.csv')
with open(out, 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0]))
    w.writeheader(); w.writerows(rows)
print('wrote', out)
