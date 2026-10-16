"""room32_tick.py: room 32's keep tick block (event 14) through the real consumer, six injected [$400e][room 32][0] entries on level1_loaded.snap:
VAR 6 and VAR 7 (bytes 2282(A5)+6/+7), button 385's state bit 0 and the GOANI (verb 3) count per push.
Run from M68000/: M68000_ROOT=$PWD ATARI_NOTRACE=1 .venv/bin/python reversing/cadaver/py/secrets/overlay/l1_objects/room32_tick.py"""
import sys, os
ROOT = os.environ.get('M68000_ROOT') or os.getcwd()
sys.path.insert(0, ROOT + '/reversing/cadaver/py/secrets/overlay/l1_objects')
import souls_chain as S
from souls_chain import HH, A5, live_res, SNAP1, push
h = HH.H(SNAP1)
g3 = h.tab[3]
for i in range(7):
    v = h.r.mem(A5 + 2282 + 6, 2); b385 = h.r.b(live_res(h, 6, 385) + 3)
    print('before push %d: VAR6=%d VAR7=%d 385.b3=%02x' % (i + 1, v[0], v[1], b385))
    if i == 6: break
    push(h, [(0x400e, live_res(h, 3, 32), 0)])
    hh = h.r.hits(1000000, 0xfe24, 0xfe36, g3)
    print('   match %d gate_ok %d GOANI %d' % (hh.get(0xfe24, 0), hh.get(0xfe36, 0), hh.get(g3, 0)))
h.close()
