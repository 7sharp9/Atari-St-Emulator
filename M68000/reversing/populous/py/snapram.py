"""snapram.py - RAM from an emulator snapshot.  ram(path) -> bytes (0..end of RAM, absolute addresses).
   CLI: python snapram.py <snap> <hexaddr> <len>   (hex dump)"""
import struct,sys
def ram(path):
    s=open(path,'rb').read(); off=5+19*4+2; ln=struct.unpack_from('<I',s,off)[0]; return s[off+4:off+4+ln]
if __name__=='__main__':
    r=ram(sys.argv[1]); a=int(sys.argv[2],16); n=int(sys.argv[3],16) if sys.argv[3].startswith('0x') else int(sys.argv[3])
    for i in range(0,n,16): print('%06x: %s'%(a+i, r[a+i:a+min(16,n-i)].hex(' ')))
