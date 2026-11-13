"""Writers of the decorated-wall list (fed $1bd58, 100 x (x, y, picture, n)) during one generator call (gen.py's entry).
Prints writer PCs with counts, and every write of a picture byte equal to 1.
Usage: picwatch.py d0,d1,d2,d3"""
import os, sys
from collections import Counter
here = os.path.dirname(os.path.abspath(__file__))
d = here
while not os.path.exists(os.path.join(d, 'tools', 'rdis.py')):
    d = os.path.dirname(d)
sys.path.insert(0, os.path.join(d, 'reversing', 'captive', 'py', 'mapgen'))
from gen import R, start  # noqa: E402
from stclient import StServer  # noqa: E402
args = [int(x, 0) for x in sys.argv[1].split(',')]
s = StServer(R)
s('load', snapshot=os.path.join(R, 'scratchpad', 'captive', 'mg_ret.snap'))
wid = s('watch_add', lo=0x1bd58, hi=0x1bd58 + 399, kind='w')['id']
start(s, *args)
r = s('watch_events', id=wid); ev = r['events'] if isinstance(r, dict) else r
print('raw', str(ev)[:300])
ev = ev[0]['events'] if ev and 'events' in ev[0] else ev
print('events', len(ev), Counter(e['pc'] for e in ev))
num = lambda v: int(v.lstrip('$'), 16) if isinstance(v, str) else v   # stserver reports addresses and values as '$hex'
for e in ev:
    a, val = num(e['addr']) - 0x1bd58, num(e['value'])
    if e['width'] == 1 and a % 4 == 2 and val == 1:
        print('picture 1 write', e)
    if e['width'] >= 2 and a % 4 == 2:
        print('picture/n word write', e)
s.close()
