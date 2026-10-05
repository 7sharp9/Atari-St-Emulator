"""hist.py <kind> <trace>...: frames per (+2,+3,+4) over the traces for the spawned record ($ff8c28) of the given kind (+19), and the 3-value (+66) held frames."""
import sys, collections
from fr import *
r=0xff8c28; kind=int(sys.argv[1])
c=collections.Counter(); held=collections.Counter(); tot=0
for p in sys.argv[2:]:
    for f,buf in frames(p):
        if b(buf,r)==0 or b(buf,r+19)!=kind: continue
        tot+=1
        c[(b(buf,r+2),b(buf,r+3),b(buf,r+4))]+=1
        if b(buf,r+66): held[(b(buf,r+2),b(buf,r+3),b(buf,r+66))]+=1
print('kind',kind,'frames',tot)
for k,v in sorted(c.items()): print('  +2=%02x +3=%02x +4=%02x  %d'%(k+(v,)))
print('held (+66!=0):',{('%02x'%a,'%02x'%b_,'%02x'%d):v for (a,b_,d),v in sorted(held.items())})
