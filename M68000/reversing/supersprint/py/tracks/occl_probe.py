import sys; sys.path.insert(0,'.')
from tkcommon import *
import trackrender as TR, occlusion as O, numpy as np
from collision import plane_from_ram
T=5
g=TR.Gfx(); idx=planar_to_idx(g.tiles(T)); mine=O.occlusion(g,T,idx)
r=Repl2(out('snaps','pre_%d.snap'%T))
for stop in ('be50','be5a','beb2'):
    o,reg=r.cmd2('bpc %s 1 30000000'%stop)
    p=out('snaps','mid_%s.snap'%stop); r.cmd('snap '+p)
    live=plane_from_ram(load_snap(p),0x61436+16000)
    print(stop,hex(reg['PC']),'mismatch vs my occlusion',int((live!=mine).sum()))
r.close()
