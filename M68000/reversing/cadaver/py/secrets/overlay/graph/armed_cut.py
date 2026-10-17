"""armed_cut.py: relaxed closure (spells, doors $07/$08 cut) from $CAD_LINEAGE_SNAP as is, and with only lever 225's state bit 0 set (room 12 armed)."""
import sys, os
sys.path.insert(0, os.environ['M68000_ROOT'] + '/reversing/cadaver/py/secrets/overlay/graph')
from sim import Sim
from relax import Relaxed
sm = Sim(); sm.spells = True
for armed in (0, 1):
    S = sm.initial()
    if armed: sm.setost(S, 225, b0=1)
    rx = Relaxed(sm, start=S, spells=True, no_doors=(7, 8)); rx.run()
    rooms = sorted(f[1] for f in rx.prov if f[0] == 'room')
    print('225 armed' if armed else '225 as in snapshot', 'b0 =', sm.ost(S, 225)[2], 'rooms', len(rooms),
          {g: bool(rx.reached(g)) for g in ('room:93', 'room:82', 'room:52', 'ruck:407', 'ruck:690', 'ruck:718', 'level:2')})
