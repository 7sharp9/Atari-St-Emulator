import sys; sys.path.insert(0,'.')
from tkcommon import *
r = Repl(sscfg.SNAP_ATTRACT)
r.cmd('kbd fe 80'); r.cmd('s 400000'); r.cmd('kbd fe 00'); r.cmd('s 700000')
for i in range(3):
    r.cmd('kbd fe 08'); r.cmd('s 60000'); r.cmd('kbd fe 00'); r.cmd('s 150000')
    p = out('snaps','w%d.snap'%i); r.cmd('snap '+p); render_snap(p, out('dbg','w%d.png'%i))
r.close()
