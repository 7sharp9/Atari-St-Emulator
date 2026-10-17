import sys, os
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.environ.get('M68000_ROOT') or os.path.normpath(os.path.join(HERE, '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'reversing', 'supersprint', 'py', 'physics'))
import pl
pl.OUT = os.path.join(pl.sscfg.WORK, 'agents', 'collide')
from difflib_ss import *
snap=sys.argv[1]; lo=int(sys.argv[2]); hi=int(sys.argv[3]); seed=int(sys.argv[4]); car=int(sys.argv[5])
h=Harness(snap); drv=Driver(h,seed); h.run_to(0xdf18,1,8000000)
for i in range(hi+1):
    drv.poke_input(); h.run_to(0xdf18,1); r=h.snap_ram()
    if i>=lo:
        tbl=r.gl(-4084); wp=r.g(WP+0) if False else r.arr(P.WP)[car]
        rec=[r.s16(tbl+wp*8+2*k) for k in range(4)]
        print(i,'WP',r.arr(P.WP),'gate1832',[r.g(-1832+2*k) for k in range(4)],'rec',rec,'X',r.arr(P.X)[car],'Y',r.arr(P.Y)[car],'cnt',r.g(-4076),'GATEw',[hex(r.gu(-1840+2*k)) for k in range(4)])
h.close()
