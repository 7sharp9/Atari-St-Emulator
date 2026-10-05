# drops.py : for every breakable prop placed by the tables (all stages), the prop's HUD name (tag $a name table $5bbaa, per kind) and the drop its +21 byte makes
# ($5a934: bit 7 clear = explicit type, $ff none, bit 7 set = random from the 32-byte row (+21 & $f) of $5a9e0 by LFSR & $1f, value $80 none;
#  D2 < $24 = pool-12 item type D2 (name: table $5bee2 + 32*type), D2 >= $24 = pool-6 weapon kind D2-$24)
import collections,sys
from rom import *
from placetab import *
def tname(a): return ''.join(chr(w(a+2*i)&0xff) for i in range(16) if (w(a+2*i)>>8)==0x44).strip()
PROP=[tname(0x5bbaa+w(0x5bbaa+2*k)) for k in range(19)]
ITEM=[tname(0x5bee2+32*t) for t in range(37)]
WEAP=['KNIFE','MURAMASA!','PIPE','SHELL','BOTTLE','ARROW']
def drop(c21):
    if c21&0x80==0: return explicit(c21)
    if c21==0xff: return 'none'
    row=c21&0xf; c=collections.Counter(b(0x5a9e0+row*32+i) for i in range(32))
    return 'random row %x: '%row+', '.join('%s x%d'%('none' if v==0x80 else explicit(v),n) for v,n in sorted(c.items(),key=lambda x:(x[0]==0x80,x[0])))
def explicit(v):
    return ('weapon %s'%WEAP[v-0x24]) if v>=0x24 else 'item %d %s'%(v,ITEM[v])
if __name__=='__main__':
    A0=areas(0x636e); A1=areas(0x6346)
    seen=collections.Counter()
    for s in range(6):
        for a in range(len(A1[s])):
            es=(initlist(A0[s][a]) if a<len(A0[s]) else [])+[e for m,x in trigmodes(A1[s][a])[0] for e in x]
            for e in es:
                if e['sp']==10: seen[(PROP[e['kind']] if e['kind']<19 else '?%d'%e['kind'],e['kind'],e['c21'])]+=1
    for (n,k,c21),v in sorted(seen.items(),key=lambda x:(x[0][1],x[0][2])):
        print('prop kind %2d %-10s +21=%02x x%-3d -> %s'%(k,n,c21,v,drop(c21)))
