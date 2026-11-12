import pathlib as _pl, sys as _sys; _sys.path.insert(0, str(_pl.Path(__file__).resolve().parent.parent)); _sys.path.insert(0, str(_pl.Path(__file__).resolve().parent))
from ccpaths import *
import struct
_ram=ram(ANCHOR)
TAN=[struct.unpack('>H',_ram[0x3864+2*i:0x3864+2*i+2])[0] for i in range(0x200)]
def s16(v): v&=0xffff; return v-65536 if v&0x8000 else v
def u16(v): return v&0xffff
def _h(d0,d1):               # $ab1e: d0,d1 signed words, called with d0<d1
    if d1==0: return u16(d0)
    q=((d0&0xffff)<<16)>>1   # swap/clr.w/lsr.l#1 : d0<<15 (unsigned 32-bit)
    if q&0x80000000: q-=1<<32
    qq=int(q/s16(d1))        # divs: truncates toward zero
    if not(-32768<=qq<=32767): return 0x2000   # bvc not taken: overflow
    d1l=u16(qq)
    t=(d1l<<8)&0xffffffff
    tv=TAN[(t>>16)&0xffff]
    r=t//tv if tv else t
    if r>0xffff: r=t&0xffff  # divu overflow leaves D1 unchanged (low word used)
    return u16(r<<4)
def _g(d0,d1):               # $ab0e: cmp.w D1,D0 / blt
    if s16(d0)<s16(d1): return _h(d0,d1)
    return u16(-_h(d1,d0)+0x4000)
def _f(d0,d1):               # $aafe: tst.w D1 / bpl
    if s16(d1)<0: return u16(-_g(d0,s16(-d1))+0x8000)
    return _g(d0,d1)
def atan2(d0,d1):            # $aae6 (entry), $aae2 halves both until each fits a signed word
    while not(-32768<=d0<=32767 and -32768<=d1<=32767):
        d0>>=1; d1>>=1
    if s16(d0)<0: return u16(-_f(s16(-d0),d1))   # neg.w: -32768 stays -32768
    return _f(d0,d1)
if __name__=='__main__':
    import subprocess,os,random,re
    random.seed(1)
    cases=[(4096,8192),(-5000,3000),(7000,-100),(-30,-4000),(123456,-654321),(0,5),(5,0),(-1234567,89),(32767,32767),(1000000,999999),(100,7),(3,20000)]
    for _ in range(20): cases.append((random.randint(-200000,200000),random.randint(-200000,200000)))
    lines=['callcap aae6 2000 D0=%08x D1=%08x'%(a&0xffffffff,b&0xffffffff) for a,b in cases]
    env=dict(os.environ,ATARI_NOTRACE='1')
    out=subprocess.run(['dotnet','exec',str(DLL),'resume',str(ANCHOR),'repl'],input='\n'.join(lines)+'\n',capture_output=True,text=True,env=env,cwd=str(ROOT)).stdout
    rd=[l for l in out.split('\n') if l.startswith('regdelta')]
    ok=0
    for (a,b),l in zip(cases,rd):
        m=re.search(r'D0 \$[0-9a-f]+->\$([0-9a-f]+)',l)
        obs=int(m.group(1),16)&0xffff if m else None
        if obs is None:  # D0 unchanged?
            obs='unchanged'
        p=atan2(a,b)
        if obs==p: ok+=1
        else: print('diff',(a,b),'obs',obs,'port',p,l)
    print('atan2 port match',ok,'of',len(cases),'(callcap lines',len(rd),')')
