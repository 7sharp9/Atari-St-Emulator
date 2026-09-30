"""poke_classes.py: events 18 and 26 with a POKED class byte (labelled synthetic).  The rucksack panel offers icon $c (event 18) only when the front
object's class 2476(A5) is 8 (with instance flags) or $b, and icon $f (event 26) only when it is $c ($009f80-$009fba).  CAVERN and TUNNEL hold no such
object (class_census.py: class 8 = 13 placed objects in other rooms, class $c = id 70 in room slot 64), so the front object's live-record class byte
(record+22, read at $0096e6) is set to 8 / $b / $c and everything else is a natural input: Space, then the icon panel, fire.
Start: sv_held_lever.snap (pickaxe in the rucksack, hero facing the TUNNEL lever, id 144, live record $059910)."""
from drv import *
from trial_ruck import trial_ruck
sys.path.insert(0, ROOT + '/reversing/cadaver/py/secrets/overlay')
from ov import wb
LIVE = 0x59910
SNAP = ensure('held_lever')
for cls, want in [(0x0b, 12), (0x0c, 15), (0x08, 12)]:
    def pre(r, cls=cls):
        if cls == 8:   # class 8 also needs instance flags: btst #4 and #0 of (template+12)+4 ($009f90-$009f9e)
            tm = 0x6fa0e; blk = tm + r.b(tm + 12)
            print('  template+12 =', r.b(tm + 12), 'instance flag byte +4 =', hex(r.b(blk + 4)), 'poked to |= $11')
            wb(r, blk + 4, r.b(blk + 4) | 0x11)
        wb(r, LIVE + 22, cls)
    trial_ruck(SNAP, want, 'space', label=f'class{cls:x}', pre=pre)
