"""Camera-space stage for the first cell ($16d9c) from RAM at $1835a: heights -> cam record (x', y', z)."""
import sys; sys.path.insert(0,__import__('os').path.dirname(__import__('os').path.abspath(__file__)))
from mw import R
r=R(sys.argv[1])
A3=r.l(0x12ce6)
def s16(v): v&=0xffff; return v-0x10000 if v&0x8000 else v
def s32(v): v&=0xffffffff; return v-(1<<32) if v&(1<<31) else v
def hi(v): return s16((v&0xffffffff)>>16)       # swap -> low word
def vert(A0,D0,D1,D2):
    h=r.sw(A0)-r.sw(0x1721c)
    D4=s32(h*r.sw(0x17212)+D1); D5=s32(h*r.sw(0x17210)+D2); D3=D0
    X,Y,Z=hi(D3),hi(D4),hi(D5)
    c,s=r.sw(0x17216),r.sw(0x17214)
    return (X*c-Y*s, Y*c+X*s, Z)
A0=r.l(0x12c80); D0,D1,D2=r.sl(0x12c72),r.sl(0x12c76),r.sl(0x12c7a)
rs=[r.sl(a) for a in (0x171fc,0x17204,0x1720c)]; cs=[r.sl(a) for a in (0x171f8,0x17200,0x17208)]
print('A0',hex(A0),'D0..2',D0,D1,D2,'row step',rs,'col step',cs,'matrix',r.sw(0x17216),r.sw(0x17214),'camh',r.sw(0x1721c),'scales',r.sw(0x17212),r.sw(0x17210))
A5=r.l(0x18f02)
seq=[]
a,d=A0,[D0,D1,D2]
seq.append(('P0',14,(a,list(d))))
a-=400; d=[d[i]+rs[i] for i in range(3)]; seq.append(('P1',350,(a,list(d))))
a+=4;   d=[d[i]+cs[i] for i in range(3)]; seq.append(('P2',366,(a,list(d))))
a+=400; d=[d[i]-rs[i] for i in range(3)]; seq.append(('P3',30,(a,list(d))))
ok=0
for n,off,(a,d) in seq:
    c=r.w(A5+off); rec=A3+c
    got=(r.sl(rec),r.sl(rec+4),r.sw(rec+10))
    exp=vert(a,*d); exp=tuple(s32(e) for e in exp[:2])+(exp[2],)
    print(n,hex(a),'h',r.sw(a),'got',got,'model',exp, 'OK' if got==exp else 'DIFF'); ok+=got==exp
print('first-cell vertices matching',ok,'/4')
