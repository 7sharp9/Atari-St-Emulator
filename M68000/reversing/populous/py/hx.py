"""hx.py <snap|img> <hexaddr> <len> : hex dump (runtime addresses). For .img use base $ad58."""
import sys,struct,os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
def load(p):
    if p.endswith('.img'):
        b=open(p,'rb').read(); return bytes(0xad58)+b
    import snapram; return snapram.ram(p)
def w(r,a): return struct.unpack_from('>H',r,a)[0]
def sw(r,a): return struct.unpack_from('>h',r,a)[0]
def l(r,a): return struct.unpack_from('>I',r,a)[0]
if __name__=='__main__':
    r=load(sys.argv[1]); a=int(sys.argv[2],16); n=int(sys.argv[3],0)
    for i in range(0,n,16):
        ch=r[a+i:a+i+min(16,n-i)]
        print('%06x: %-48s %s'%(a+i,ch.hex(' '),''.join(chr(c) if 32<=c<127 else '.' for c in ch)))
