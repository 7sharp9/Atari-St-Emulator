# per (stage, area): init-list and trigger-list entry counts by spawner type, trigger mode, trigger range, pool-8 kinds and pool-a prop kinds placed
import collections
from placetab import *
A0=areas(0x636e); A1=areas(0x6346)
POOL={2:'fighters',4:'boss',6:'weapons',8:'objects',10:'props',12:'slot ffb228',18:'items',20:'debris'}
for s in range(6):
    for a in range(len(A1[s])):
        ini=initlist(A0[s][a]) if a<len(A0[s]) else []
        segs,_=trigmodes(A1[s][a]); tr=[e for m,x in segs for e in x]
        ci=collections.Counter(POOL[e['sp']] for e in ini); ct=collections.Counter(POOL[e['sp']] for e in tr)
        k8=sorted(set('%x'%e['kind'] for e in ini+tr if e['sp']==8))
        ka=sorted(set('%x'%e['kind'] for e in ini+tr if e['sp']==10))
        k2=sorted(set('%x'%e['kind'] for e in ini+tr if e['sp']==2))
        trg=[e['trig'] for e in tr]
        print('stage %d area %d: modes %s init %s (%d) trig %s (%d) trigger %s..%s | fighter kinds %s pool8 kinds %s props %s'%(s,a,[m for m,x in segs],dict(ci),len(ini),dict(ct),len(tr),('%x'%min(trg)) if trg else '-',('%x'%max(trg)) if trg else '-',k2,k8,ka))
