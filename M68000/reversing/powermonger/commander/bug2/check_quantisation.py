import pickle,sys
sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parent))
import follow, astar
from collections import Counter
d=pickle.load(open(follow.DATA/'pairs.pkl','rb')); P=d['pairs']
R=pickle.load(open(follow.DATA/'results.pkl','rb'))
trs={}; c=Counter()
for i,r in R.items():
    if r['cls']!='b': continue
    p=P[i]
    for nm,h in (('L',1),('R',-1)):
        if r['algos']['bug2_'+nm]['ok']: continue
        if p['plane'] not in trs: trs[p['plane']]=follow.Terrain(astar.Map(str(follow.ROOT/'scratchpad/pm148/arms/long'/(p['snap']+'.snap'))))
        for tn,a0 in ((8,16),(4,16),(4,8)):
            res=follow.run(trs[p['plane']],(p['x'],p['y']),(p['tx'],p['ty']),p['speed'],'bug2',h,a0=a0,turn=tn)
            c[(nm,tn,a0,res['why'])]+=1
for k in sorted(c): print(k,c[k])
