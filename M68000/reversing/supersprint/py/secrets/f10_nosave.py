"""f10_nosave.py - F10 during a race returns 1 from $be40 and the session tail skips `jsr 102(A5)` ($1000e = write SSPRINT.HSC); a session that ends
because every human is eliminated (ss_race0 winner's circle -> fires) does reach $1000e.  Counts entries of $1000e (HSC writer) in both."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from probe import *
r = R(sscfg.SNAP_RACE)
a = Acc(r, [0x1000e, 0x1399e, 0xc9de])
a.run(1000000); a.press(['44'], 60000); a.run(4000000)
print('F10 abort in race       : HSC writer $1000e entered', a.tot[0x1000e], 'times; back in attract wait loop', a.tot[0x1399e])
r.close()
r = R(sscfg.SNAP_RESULTS)
a = Acc(r, [0x1000e, 0x1399e])
a.run(1000000)
for i in range(8):
    a.kbd('fe', '80'); a.run(60000); a.kbd('fe', '00'); a.run(3000000)
    if a.tot[0x1000e]: break
print('normal end (all humans out): HSC writer $1000e entered', a.tot[0x1000e], 'times; back in attract wait loop', a.tot[0x1399e])
r.close()
