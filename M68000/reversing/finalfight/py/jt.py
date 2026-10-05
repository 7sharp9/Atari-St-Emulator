# word-offset jump tables: `move.w 6(PC,Dn.w),D1 / jmp 2(PC,D1.w)` at M: table at M+8, entries relative to M+8.
import sys
from rd import rom
def jt(m):
    base=m+8
    n=int.from_bytes(rom[base:base+2],'big')//2
    n=min(n,64)
    return [(i,base+int.from_bytes(rom[base+2*i:base+2*i+2],'big')) for i in range(n)]
if __name__=='__main__':
    for a in sys.argv[1:]:
        m=int(a,16); print('%x:'%m,' '.join('%d->%x'%(i,t) for i,t in jt(m)))
