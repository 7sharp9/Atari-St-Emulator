"""script_ents.py <tag> <kind>: unique stage-script entries (set 2 = $5f7e, the set in use: $726e0 = 2) of one pool tag and kind, sorted by address."""
import sys
from script import *
tag=int(sys.argv[1]); kind=int(sys.argv[2])
seen={}
for si in range(8):
    p=l(0x5f7e+4*si); n=w(p)//2
    for ai in range(n):
        a=p+w(p+2*ai)
        for it in parse(a):
            if it[0]!='seg': continue
            s=it[1]
            for e in s['ents']:
                if e['tag']==tag and e['kind']==kind and e['addr'] not in seen:
                    seen[e['addr']]=(si,ai,s,e)
for addr,(si,ai,s,e) in sorted(seen.items()):
    y=e['y']; ys='%d(+rand)'%(y&0x7fff) if y<0 else str(y)
    print('stage %d area %d  seg trigger cam=%04x  entry $%x  sub +20=%02x +21=%02x  delay %3d track %d x=%5d y=%s  lvl=%02x 2p-only=%d  cont=%d'%(si,ai,s['trigger'],addr,e['w20']>>8,e['w20']&255,e['delay'],e['track'],e['x'],ys,e['lvl'],e['p2'],s['cont']))
print('entries',len(seen))
