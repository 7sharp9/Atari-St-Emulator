import sys
sys.path.insert(0,'.')
from rd import rom
def callers(t):
    out=[]
    for a in range(0,0x100000-6,2):
        w=int.from_bytes(rom[a:a+2],'big')
        if w in (0x6100,0x6000):
            d=int.from_bytes(rom[a+2:a+4],'big'); d=d-0x10000 if d&0x8000 else d
            if a+2+d==t: out.append((a,'bsr' if w==0x6100 else 'bra'))
        elif w in (0x4eb8,0x4ef8):
            if int.from_bytes(rom[a+2:a+4],'big')==t: out.append((a,'jsr' if w==0x4eb8 else 'jmp'))
        elif w in (0x4eb9,0x4ef9):
            if int.from_bytes(rom[a+2:a+6],'big')==t: out.append((a,'jsr.l' if w==0x4eb9 else 'jmp.l'))
        elif (w&0xff00) in (0x6100,0x6000) and (w&0xff) not in (0,0xff):
            d=w&0xff; d=d-256 if d&0x80 else d
            if a+2+d==t: out.append((a,'bsr.s' if (w&0xff00)==0x6100 else 'bra.s'))
        elif (w&0xf000)==0x6000 and (w&0xff)==0 and (w&0xf00) not in (0,0x100):
            d=int.from_bytes(rom[a+2:a+4],'big'); d=d-0x10000 if d&0x8000 else d
            if a+2+d==t: out.append((a,'bcc'))
    return out
if __name__=='__main__':
    for t in sys.argv[1:]:
        print(t, ['%06x %s'%x for x in callers(int(t,16))])
