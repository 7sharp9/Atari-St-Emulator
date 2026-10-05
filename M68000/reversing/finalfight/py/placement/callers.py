# direct callers / literal references of addresses: callers.py 4536 4632 ...
import sys
from rom import *
def callers(t):
    out=[]
    for a in range(0,0x100000-6,2):
        v=w(a)
        if v in (0x6100,0x6000):
            d=sw(a+2)
            if a+2+d==t: out.append((a,'bsr' if v==0x6100 else 'bra'))
        elif v in (0x4eb8,0x4ef8):
            if w(a+2)==t: out.append((a,'jsr' if v==0x4eb8 else 'jmp'))
        elif v in (0x4eb9,0x4ef9):
            if l(a+2)==t: out.append((a,'jsr.l' if v==0x4eb9 else 'jmp.l'))
        elif (v&0xff00) in (0x6100,0x6000) and (v&0xff) not in (0,0xff):
            d=v&0xff; d=d-256 if d&0x80 else d
            if a+2+d==t: out.append((a,'bsr.s' if (v&0xff00)==0x6100 else 'bra.s'))
        elif (v&0xf000)==0x6000 and (v&0xff)==0 and (v&0xf00) not in (0,0x100):
            if a+2+sw(a+2)==t: out.append((a,'bcc'))
        elif v&0xf1ff==0x207c or v&0xf1ff==0x203c or v==0x2ebc or v&0xf1c0==0x2000 and (v&0x3f)==0x3c:
            if l(a+2)==t: out.append((a,'imm.l'))
    return out
if __name__=='__main__':
    for t in sys.argv[1:]:
        print(t, ['%06x %s'%x for x in callers(int(t,16))])
