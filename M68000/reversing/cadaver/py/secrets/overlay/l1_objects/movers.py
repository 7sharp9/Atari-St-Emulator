"""movers.py SNAP ID...: each object's live record header, mover state and mover program (secrets.md event 12: state byte at rec + rec[13], cursor +1, program from +14;
opcodes 0 step `00 dx dy dz`, 1 skip, 2 stop, 3 delay, 4 event).  Room 6's key 251, flask 219 and sack 221 read `00 08 00 00 02`: +8 in x, stop (then a fall);
the gate 620 `00 00 00 30 02`: +48 in z.  A template whose rec[13] does not point at a mover (the ledge 392) prints bytes that are not a program.
Run from M68000/: M68000_ROOT=$PWD ATARI_NOTRACE=1 .venv/bin/python reversing/cadaver/py/secrets/overlay/l1_objects/movers.py <snap> 251 219 221 620"""
import sys, os
def _root():
    if os.environ.get('M68000_ROOT'): return os.environ['M68000_ROOT']
    d = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(d, 'tools', 'rdis.py')):
        assert os.path.dirname(d) != d, 'repo root (tools/rdis.py) not found: set M68000_ROOT'
        d = os.path.dirname(d)
    return d
ROOT = _root(); os.environ.setdefault('M68000_ROOT', ROOT); os.environ.setdefault('ATARI_NOTRACE', '1')
ARGS = [os.path.abspath(a) if a.endswith('.snap') else a for a in sys.argv[1:]]   # lib/drv.py chdirs on import
sys.path.insert(0, ROOT + '/reversing/cadaver/py/secrets/overlay/action/exit_level0/l1')
from explore import *
r = Repl(ARGS[0])
for o in [int(a) for a in ARGS[1:]]:
    a = live_rec(r, o)
    if not a: print(o, 'not live'); continue
    rec = r.mem(a, 16); off = rec[13]
    print('obj %d rec %x hdr %s  state@+%d %s  program@+%d %s' % (o, a, rec.hex(' '), off, r.mem(a + off, 2).hex(' '), off + 14, r.mem(a + off + 14, 24).hex(' ')))
r.close()
