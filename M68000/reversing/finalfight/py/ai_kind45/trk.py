"""trk.py <trace> <record addr hex> [lo hi]: print the transitions of (b0,+2,+3,+4,+5,+66) of one record with x, y, hp, +44/+45, +30/+31, Cody hp."""
import sys
from fr import *
path=sys.argv[1]; r=int(sys.argv[2],16)
lo=int(sys.argv[3]) if len(sys.argv)>3 else 0
hi=int(sys.argv[4]) if len(sys.argv)>4 else 1<<30
prev=None; hist={}
first=None
for f,buf in frames(path):
    if first is None: first=f
    if f-first<lo or f-first>hi: continue
    st=(b(buf,r),b(buf,r+2),b(buf,r+3),b(buf,r+4),b(buf,r+5),b(buf,r+66))
    hist[st]=hist.get(st,0)+1
    if st!=prev:
        print('%5d(+%4d) b0=%02x s2=%02x s3=%02x s4=%02x s5=%02x s66=%02x x=%04x y=%04x hp=%04x 44/45=%02x/%02x 30=%02x 31=%02x 54=%02x 46=%02x cody x=%04x hp=%04x'%((f,f-first)+st+(w(buf,r+6),w(buf,r+10),w(buf,r+24),b(buf,r+44),b(buf,r+45),b(buf,r+30),b(buf,r+31),b(buf,r+54),b(buf,r+46),w(buf,0xff856e),w(buf,0xff8580))))
        prev=st
print('state histogram (b0,s2,s3,s4,s5,s66) -> frames')
for k,v in sorted(hist.items()): print('  ',' '.join('%02x'%x for x in k),v)
