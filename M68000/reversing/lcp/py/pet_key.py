"""Ctrl-P (pet) from a seated state (README, "Control keys and house events"): Ctrl-C makes the phone ring, the run
stops when `$21a8c` sets the seated flag `$2c944`, and from that fork Ctrl-P is pressed or not (control). Reports the
happiness words and the pet flag `$2c946` over the following window.

usage: pet_key.py [window_steps]
Needs $LCP_WORK (default <root>/scratchpad/lcp) holding house.snap and disk/tmbird03_even.st.
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
root = os.environ.get('M68000_ROOT') or HERE
while not os.path.exists(os.path.join(root, 'tools', 'rdis.py')):
    root = os.path.dirname(root)
WORK = os.environ.get('LCP_WORK') or os.path.join(root, 'scratchpad', 'lcp')
sys.path.insert(0, os.path.join(root, 'tools'))
from stclient import StServer  # noqa: E402

WIN = int(float(sys.argv[1])) if len(sys.argv) > 1 else 20_000_000
WATCH = {'happy': 0x5144e, 'happy_left': 0x51456, 'happy_dir': 0x51458, 'pet': 0x2c946, 'seated': 0x2c944}


def ctrl(s, scan):
    for b in (0x1d, scan, scan | 0x80, 0x9d):
        s('kbd', bytes=[b]); s('run', max_steps=15000 if b == scan else 2000)


def words(s):
    return {k: int.from_bytes(s.read(a, 2), 'big') for k, a in WATCH.items()}


s = StServer(root)
s('load', snapshot=os.path.join(WORK, 'house.snap'), disk=os.path.join(WORK, 'disk', 'tmbird03_even.st'))
ctrl(s, 0x2e)
w = s('watch_add', lo=0x2c944, hi=0x2c945, kind='w', value=1, mask=0xffff, stop=True)['id']
r = s('run', max_steps=200_000_000)
print('seated stop:', r['reason'], r['steps'], words(s))
s('watch_remove', id=w)
s('run', max_steps=200_000)          # let the sit animation start before the key
base = s('fork')['id']
for arm in ('control', 'ctrl-P'):
    s('restore', id=base)
    ids = {s('watch_add', lo=a, hi=a + 1, kind='w', max_events=200)['id']: k for k, a in WATCH.items()}
    if arm == 'ctrl-P':
        ctrl(s, 0x19)
    s('run', max_steps=WIN)
    ev = {}
    for i, k in ids.items():
        e = s('watch_events', id=i)[0]['events']
        if e:
            ev[k] = [(x['pc'], x['value']) for x in e][:6]
        s('watch_remove', id=i)
    print(f'{arm}: writes {ev}; end {words(s)}', flush=True)
s.close()
