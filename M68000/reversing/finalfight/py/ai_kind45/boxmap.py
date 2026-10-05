"""boxmap.py <rec> <kind> <trace>...: for frames of a live record of the given kind, count (+2,+3,+4,+66, attack box +45) over frames with an attack box; plus +74 (armed)."""
import sys, collections
from fr import *
r=int(sys.argv[1],16); kind=int(sys.argv[2])
c=collections.Counter(); armed=collections.Counter()
for p in sys.argv[3:]:
    for f,buf in frames(p):
        if b(buf,r)==0 or b(buf,r+19)!=kind: continue
        a=b(buf,r+45)
        if a: c[(b(buf,r+2),b(buf,r+3),b(buf,r+4),a&0x7f)]+=1; armed[(b(buf,r+3),b(buf,r+4),a&0x7f,b(buf,r+74))]+=1
for k,v in sorted(c.items()): print('s2=%02x s3=%02x s4=%02x box45=%02x frames=%d'%(k+(v,)))
print('armed(+74) at attack frames: (s3,s4,box,+74):'); 
for k,v in sorted(armed.items()): print('  %02x %02x %02x %02x  %d'%(k+(v,)))
