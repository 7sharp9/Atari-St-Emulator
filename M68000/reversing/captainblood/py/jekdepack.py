"""Depack 'JEK!' files (Pack-Ice 2.x style long-word bitstream, read backwards).
Transcribed from the trap-#1 hook in PACT3.TOS (text $ab30-$acdc, loaded at $aaa0):
trailer = [..bit buffer long][D5 checksum seed][unpacked size][JEK!]; written backwards.
usage: jekdepack.py in out   |   --all dir outdir"""
import sys,struct,os
def depack(b):
    assert b[-4:]==b'JEK!', 'no JEK! trailer'
    n=len(b); size=struct.unpack('>I',b[n-8:n-4])[0]
    p=n-8
    def lng():
        nonlocal p
        p-=4; return struct.unpack('>I',b[p:p+4])[0]
    d5=lng(); d0=lng(); d5^=d0
    out=bytearray(size); a2=size
    def bit():
        nonlocal d0,d5
        c=d0&1; d0>>=1
        if d0==0:
            d0=lng(); d5^=d0; c=d0&1; d0=(d0>>1)|0x80000000
        return c
    def bits(k):
        v=0
        for _ in range(k): v=(v<<1)|bit()
        return v
    def copy(d3,d1):
        nonlocal a2
        off=bits(d1)
        for _ in range(d3+1):
            a2-=1; out[a2]=out[a2+off]
    while a2>0:
        if bit()==0:
            if bit()==1: copy(1,8)
            else:
                lit(bits(3),0) if False else None
                d3=bits(3)
                for _ in range(d3+1):
                    a2-=1; out[a2]=bits(8)
        else:
            d2=bits(2)
            if d2<2: copy(d2+2,9+d2)
            elif d2==3:
                d3=bits(8)+8
                for _ in range(d3+1):
                    a2-=1; out[a2]=bits(8)
            else:
                d3=bits(8); copy(d3,12)
    return bytes(out),d5
if __name__=='__main__':
    if sys.argv[1]=='--all':
        for f in sorted(x for x in os.listdir(sys.argv[2]) if os.path.isfile(os.path.join(sys.argv[2],x))):
            b=open(os.path.join(sys.argv[2],f),'rb').read()
            if b[-4:]==b'JEK!':
                try:
                    o,d5=depack(b); open(os.path.join(sys.argv[3],f),'wb').write(o); print(f,len(b),'->',len(o),'checksum residue',hex(d5))
                except Exception as e: print(f,'FAIL',e)
    else:
        o,d5=depack(open(sys.argv[1],'rb').read()); open(sys.argv[2],'wb').write(o); print(len(o),hex(d5))
