"""poke_class8.py: class 8 container path of icon $c ($a682): with the front object's class poked to 8 and its first instance word cleared, the held item
is written into that word ($a6a6 move.w 4(A1),(A0)), removed from the rucksack ($a7fe -> $c3d4) and event 18 is queued.  SYNTHETIC (pokes: live class byte
and instance block); the natural class-8 objects (13 in other rooms) are not reachable from CAVERN/TUNNEL without a room walk."""
from drv import *
from trial_ruck import trial_ruck
sys.path.insert(0, ROOT + '/reversing/cadaver/py/secrets/overlay')
from ov import wb, ww
LIVE = 0x59910; TM = 0x6fa0e
def pre(r):
    blk = TM + r.b(TM + 12)
    print('  instance block @$%x before:' % blk, r.mem(blk, 8).hex())
    wb(r, blk + 4, r.b(blk + 4) | 0x11)   # bit 4 and bit 0 gates ($009f90/$009f98)
    ww(r, blk, 0)                          # free slot: tst.w (A0) at $a6a2
    wb(r, LIVE + 22, 8)
    print('  instance block after poke:', r.mem(blk, 8).hex())
    globals()['BLK'] = blk
tot, evs = trial_ruck(ensure('held_lever'), 12, 'space', label='class8free', pre=pre)
r = Repl(OUT + 'tr_class8free_12.snap'); blk = TM + r.b(TM + 12)
print('after: instance block', r.mem(blk, 8).hex(), 'count 2438', r.a5(2438,1).hex(), 'item rec 10(A1)=', r.b(0x6fc56 + 10))
r.close()
