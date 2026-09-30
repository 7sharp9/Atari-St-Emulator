import sys; sys.path.insert(0,'.')
from tkcommon import *
import attrmap as AM
T=7; mine=AM.attr_map(T)
r=Repl2(out('snaps','pre_%d.snap'%T))
for stop in ('15550','be50','beb2'):
    o,reg=r.cmd2('bpc %s 1 30000000'%stop)
    ptr=int.from_bytes(r.mem(A4-1910,4),'big')
    live=r.mem(ptr,1000)
    print(stop, hex(reg['PC']), 'cells 234..238 live', live[234:239].hex(' '), 'mine', mine[234:239].hex(' '), 'total diffs', sum(1 for a,b in zip(mine,live) if a!=b))
r.close()
