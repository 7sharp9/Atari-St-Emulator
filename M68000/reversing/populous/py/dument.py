"""dument.py <snap> : dump the walker/settlement array at $3b278 (0x16 bytes x count $3c4e2)."""
import sys,struct
import os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from snapram import ram
def ents(r):
    n=struct.unpack_from('>h',r,0x3c4e2)[0]
    out=[]
    for i in range(n):
        a=0x3b278+0x16*i
        f,side,b2,b3,stren,t6,cell,off,st,tgt,last,b14,b15=struct.unpack_from('>BBBBhhhhhIhBB',r,a)
        out.append(dict(i=i,flags=f,side=side,b2=b2,b3=b3,str=stren,t6=t6,cell=cell,off=off,st=st,tgt=tgt,last=last,b14=b14,b15=b15))
    return out
if __name__=='__main__':
    r=ram(sys.argv[1])
    for e in ents(r):
        c=e['cell']; print('%3d fl=%02x side=%d b2=%d b3=%2d str=%5d t6=%5d cell=%04x(x%2d,y%2d) off=%5d st=%3d tgt=%08x last=%04x b14=%02x'%(e['i'],e['flags'],e['side'],e['b2'],e['b3'],e['str'],e['t6'],c,c&63,c>>6,e['off'],e['st'],e['tgt'],e['last'],e['b14']))
