import sys, os
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.environ.get('M68000_ROOT') or os.path.normpath(os.path.join(HERE, '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'reversing', 'supersprint', 'py', 'physics'))
import pl
pl.OUT = os.path.join(pl.sscfg.WORK, 'agents', 'collide')
from difflib_ss import *
h=Harness(sys.argv[1])
h.run_to(0xdf18,1,8000000)
for i in range(int(sys.argv[2])):
    regs=h.run_to(0xaa60,1,400000)
    if regs is None: print('no'); break
    sp=regs['A7']; out,_=h.cmd('m %x 6'%(sp)); 
    r=h.snap_ram()
    print(i,out[-1] if out else None,'R',r.gu(-8072),'cnt',r.g(-1808),'tbl1278',[r.g(-1278+2*k) for k in range(8)],'-1814',[r.g(-1814+2*k) for k in range(3)],'-1820',[r.g(-1820+2*k) for k in range(3)],'-1826',[r.g(-1826+2*k) for k in range(3)],'-1832',[r.g(-1832+2*k) for k in range(3)])
    h.cmd('s 20')
h.close()
