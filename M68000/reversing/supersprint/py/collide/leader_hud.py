"""leader_hud.py - consumer 1 of the tripwire counter: $13bbe (HUD refresh, thunk 270(A5)) redraws one HUD panel per 2 frames.
 Every 4th pass of R%6==0 it recomputes the leader L = $13b34 into -4812.  Slot k = (R%6)>>1 (0..2):
   k != L or pass counter -4814 > 1 : normal panel redraw ($158ea,$15e5a);   k == L and counter == 0 : $13c50(k) blits the leader marker.
 Test: poke tripwire counts so car j leads (others 0, laps/sectors equal), run 3 full 24-frame cycles, record every call of $13c50 (slot argument at SP+4)
 and of $158ea (slot at SP+8) with its frame counter -8072.  Expected: $13c50 is called for slot j only (never for j == 3, which has no panel), once per cycle,
 and $158ea for that slot is skipped on the pass right after the marker (counter 1) and runs on counters 2 and 3.
 usage: leader_hud.py <snap>"""
import sys, os
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.environ.get('M68000_ROOT') or os.path.normpath(os.path.join(HERE, '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'reversing', 'supersprint', 'py', 'physics'))
import pl
pl.OUT = os.path.join(pl.sscfg.WORK, 'agents', 'collide')
from difflib_ss import *
import re
snap = sys.argv[1]
if __name__ == '__main__':
    for j in range(4):
        h = Harness(snap); h.run_to(0xdf18, 1, 8000000)
        pl.poke_arr(h, -3906, [1] * 4); pl.poke_arr(h, -3850, [2] * 4)
        pl.poke_arr(h, -3842, [50 if i == j else 0 for i in range(4)])
        ev = []
        budget = 24 * 12000 * 3
        used = 0
        # run in chunks, using bpc on 13c50 then 158ea alternately would lose ordering; use a watch-free approach: bpc on 13c50 only, plus panel via separate run
        marker = []
        while used < budget:
            regs = h.run_to(0x13c50, 1, budget - used)
            if regs is None: break
            sp = regs['A7']; out, _ = h.cmd('m %x 6' % sp)
            line = [l for l in out if re.match(r'^([0-9a-f]{2} )+[0-9a-f]{2}$', l.strip())]
            b = [int(x, 16) for x in line[0].split()]
            slot = (b[4] << 8) | b[5]
            r = h.snap_ram()
            marker.append((slot, r.gu(-8072), r.g(-4814), r.g(-4812)))
            h.cmd('s 40'); used += 40 + 1
        print('leader poked = car %d: $13c50 calls (slot, R, counter, -4812) = %s' % (j, marker))
        h.close()
