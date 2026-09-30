import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pl import *
for snap in [sscfg.SNAP_RACE, sscfg.SNAP_ATTRACT, sscfg.SNAP_RESULTS]:
    r = Ram(snap)
    print(os.path.basename(snap))
    for off in [-78, -82, -86, -90, -94, -98, -3602, -1722, -1910, -4944, -1196, -8076, 142]:
        print('  %6d(A4) -> %08x' % (off, r.gl(off)))
