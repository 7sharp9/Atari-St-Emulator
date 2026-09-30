import sys; sys.path.insert(0,'.')
from tkcommon import *
T=int(sys.argv[1]) if len(sys.argv)>1 else 5
r = Repl2(sscfg.SNAP_ATTRACT)
r.cmd('kbd fe 80'); r.cmd('s 400000'); r.cmd('kbd fe 00'); r.cmd('s 700000')
o, reg = r.cmd2('bpc 19646 1 400000')
a6 = reg['A6']; dial = int.from_bytes(r.mem(a6-4, 2), 'big')
while dial != 2*T:
    r.cmd('kbd fe 08'); r.cmd('s 60000'); r.cmd('kbd fe 00'); r.cmd('s 150000'); dial = int.from_bytes(r.mem(a6-4, 2), 'big')
r.cmd('kbd fe 80'); r.cmd('s 60000'); r.cmd('kbd fe 00'); r.cmd('s 1500000')
r.cmd('kbd 2a'); r.cmd('s 300000'); r.cmd('kbd aa'); r.cmd('s 300000')
r.cmd('kbd fe 80'); r.cmd('s 300000'); r.cmd('kbd fe 00')
for i in range(10):
    o,reg=r.cmd('s 1000000'); 
    p=out('snaps','d5_%d.snap'%i); r.cmd('snap '+p); render_snap(p,out('dbg','d5_%d.png'%i)); print(i,hex(reg['PC']),flush=True)
r.close()
