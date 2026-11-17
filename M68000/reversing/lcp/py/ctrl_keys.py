"""Drive the control keys that `$26fe0` handles (README, "Control keys and house events") from `house.snap`, one per
fork plus a no-key control, and report for each: the house events queued at `$2c948`, the first entry of each event
handler, writes to the key's own flags, and screenshots after the handler starts.

usage: ctrl_keys.py [budget_steps] [keys]     keys: letters from ABCDFPRW plus '-' for the no-key control
Needs $LCP_WORK (default <root>/scratchpad/lcp) holding house.snap and disk/tmbird03_even.st. Writes PNGs to
$LCP_WORK/keys/.
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
root = os.environ.get('M68000_ROOT') or HERE
while not os.path.exists(os.path.join(root, 'tools', 'rdis.py')):
    root = os.path.dirname(root)
WORK = os.environ.get('LCP_WORK') or os.path.join(root, 'scratchpad', 'lcp')
sys.path.insert(0, os.path.join(root, 'tools'))
from stclient import StServer  # noqa: E402

BUDGET = int(float(sys.argv[1])) if len(sys.argv) > 1 else 150_000_000
KEYS = sys.argv[2] if len(sys.argv) > 2 else '-ABCDFPRW'
SCAN = {'A': 0x1e, 'B': 0x30, 'C': 0x2e, 'D': 0x20, 'F': 0x21, 'P': 0x19, 'R': 0x13, 'W': 0x11}
# event -> handler, from the $1721c switch; $1fb36 alarm (from $18656), $23568 water (from $26fe0 key $17)
HANDLERS = {0x1c: 0x21f7c, 0x1d: 0x222ea, 0x1e: 0x21c30, 0x1f: 0x21f62, 0x20: 0x224ac, 0x23: 0x2310a,
            'alarm': 0x1fb36, 'water': 0x23568}
FLAGS = {'alarm $3df6c': 0x3df6c, 'ring $2ae12': 0x2ae12, 'pet $2c946': 0x2c946, 'happy $5144e': 0x5144e,
         'water $5141a': 0x5141a, 'nofood $3e26e': 0x3e26e}
PRE = {'chair $2c944': 0x2c944, 'pet $2c946': 0x2c946, 'bits $5147e': 0x5147e, 'water $5141a': 0x5141a,
       'happy $5144e': 0x5144e, 'event_block $2ae16': 0x2ae16, 'away $51418': 0x51418, 'typing $4e200': 0x4e200}
OUT = os.path.join(WORK, 'keys')
os.makedirs(OUT, exist_ok=True)


def rw(s, a):
    return int.from_bytes(s.read(a, 2), 'big')


s = StServer(root)
s('load', snapshot=os.path.join(WORK, 'house.snap'), disk=os.path.join(WORK, 'disk', 'tmbird03_even.st'))
base = s('fork')['id']
print('pre', {k: hex(rw(s, a)) for k, a in PRE.items()})
for key in KEYS:
    s('restore', id=base)
    q = s('watch_add', lo=0x2c948, hi=0x2c95b, kind='w', max_events=1000)['id']
    hid = {s('watch_add', lo=a, hi=a, kind='r', pc_lo=a, pc_hi=a, max_events=1000)['id']: n for n, a in HANDLERS.items()}
    fid = {s('watch_add', lo=a, hi=a + 1, kind='w', max_events=1000)['id']: n for n, a in FLAGS.items()}
    if key != '-':
        s('kbd', bytes=[0x1d]); s('run', max_steps=2000)
        s('kbd', bytes=[SCAN[key]]); s('run', max_steps=30000)
        s('kbd', bytes=[SCAN[key] | 0x80]); s('run', max_steps=2000)
        s('kbd', bytes=[0x9d])
    done, first = 34000 if key != '-' else 0, {}
    shots = []
    while done < BUDGET:
        r = s('run', max_steps=min(5_000_000, BUDGET - done)); done += r['steps']
        for wid, n in hid.items():
            for e in s('watch_events', id=wid)[0]['events']:
                first.setdefault(n, e['step'])
        if first and len(shots) < 3 and (not shots or done - shots[-1] >= 10_000_000):
            p = os.path.join(OUT, f'{key}_{len(shots)}.png')
            s('render', path=p); shots.append(done)
    qev = [(e['pc'], e['value']) for e in s('watch_events', id=q)[0]['events']]
    fev = {}
    for wid, n in fid.items():
        evs = s('watch_events', id=wid)[0]['events']
        if evs:
            fev[n] = [(e['pc'], e['value']) for e in evs][:6]
    print(f'key {key}: queue writes {qev[:8]}; handler first entry {({str(k) if isinstance(k, str) else hex(k): v for k, v in first.items()})}; '
          f'flag writes {fev}; shots at {shots}', flush=True)
    for wid in [q, *hid, *fid]:
        s('watch_remove', id=wid)
s.close()
