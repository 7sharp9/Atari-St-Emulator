# classify.py <S log> <W log> : every record first seen live from frame 1316 on, grouped by the pc of the instruction that created it ($61f8 = placement spawner, $5ee6 = stage script, ...)
import sys,collections
from joinS import join
res=[s for s in join(sys.argv[1],sys.argv[2]) if s['f']>=1316]
c=collections.Counter(); kinds=collections.defaultdict(set)
for s in res:
    k=(s['pool'],'%06x'%s['pc'] if s['pc'] else '??????'); c[k]+=1; kinds[k].add('%x'%s['kind'])
for k,v in sorted(c.items()): print('%3d pool %-2s created at %s kinds %s'%(v,k[0],k[1],sorted(kinds[k])))
print('total',len(res),'unattributed',sum(v for k,v in c.items() if k[1]=='??????'))
