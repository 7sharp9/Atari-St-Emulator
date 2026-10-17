"""armed_cut.py: relaxed closure (spells, doors $07/$08 cut) from $CAD_LINEAGE_SNAP three ways: as is; with only lever 225's state bit 0 set
(room 12 armed); with room 12's region block r12.1 (the un-armed hero's teleport to room 93) dropped, the edge pillars 213/214 wall off on foot."""
import sys, os
sys.path.insert(0, os.environ['M68000_ROOT'] + '/reversing/cadaver/py/secrets/overlay/graph')
from sim import Sim
from relax import Relaxed
sm = Sim(); sm.spells = True
for name, armed, drop in (('as in snapshot', 0, ()), ('225 armed', 1, ()), ('r12.1 dropped', 0, (('room', 12, 1),))):
    S = sm.initial()
    if armed: sm.setost(S, 225, b0=1)
    rx = Relaxed(sm, start=S, spells=True, no_doors=(7, 8), drop=drop); rx.run()
    rooms = sorted(f[1] for f in rx.prov if f[0] == 'room')
    print('%-15s 225 b0 = %d  rooms %d' % (name, sm.ost(S, 225)[2], len(rooms)),
          {g: bool(rx.reached(g)) for g in ('room:93', 'room:82', 'room:52', 'ruck:407', 'ruck:690', 'ruck:718', 'level:2')})
