import pickle,sys,time
from pathlib import Path
sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parent))
import follow, astar, random
d=pickle.load(open(follow.DATA/'pairs.pkl','rb'))
P=d['pairs']
snap={}
for p in P: snap.setdefault(p['plane'],p['snap'])
# fast sampler vs ref
for h,s in list(snap.items())[:2]:
    mp=astar.Map(str(follow.ROOT/'scratchpad/pm148/arms/long'/(s+'.snap')))
    tr=follow.Terrain(mp)
    bad=0
    for _ in range(20000):
        x=random.randrange(0,0x4000);y=random.randrange(0,0x2000)
        if tr.free(x,y)!=(mp.sample(x,y)!=0): bad+=1
    print(h[:6],'fast vs ref mismatches',bad,'/20000')
    q=[p for p in P if p['plane']==h and p['cls']=='b'][:6]
    for p in q:
        for algo,hand in [('bug2',1),('bug2',-1),('kclear',1),('kclear',-1)]:
            t0=time.time()
            r=follow.run(tr,(p['x'],p['y']),(p['tx'],p['ty']),p['speed'],algo,hand)
            print(p['obj'],algo,hand,r['ok'],r['why'],r['ticks'],int(r['length']),'straight',int(((p['x']-p['tx'])**2+(p['y']-p['ty'])**2)**.5),'%.2fs'%(time.time()-t0))
