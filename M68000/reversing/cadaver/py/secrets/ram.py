import struct,sys
def ram(p='scratchpad/cadaver/gameplay_empire.snap'):
    s=open(p,'rb').read(); off=5+19*4+2
    return s[off+4:off+4+0x100000]
if __name__=='__main__':
    r=ram(); a=int(sys.argv[1],16); n=int(sys.argv[2],16)
    for i in range(0,n,16):
        b=r[a+i:a+i+16]
        print('%06x  '%(a+i)+' '.join('%02x'%x for x in b)+'  '+''.join(chr(x) if 32<=x<127 else '.' for x in b))
