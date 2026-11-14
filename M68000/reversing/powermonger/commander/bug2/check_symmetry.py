import pickle,sys
sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parent))
import follow, astar
d=pickle.load(open(follow.DATA/'pairs.pkl','rb')); P=d['pairs']
p=P[0]
real=follow.Terrain(astar.Map(str(follow.ROOT/'scratchpad/pm148/arms/long'/(p['snap']+'.snap'))))
class Syn(follow.Terrain):
    def __init__(s,mp): super().__init__(mp)
    def free(s,x,y):
        if x<1000 or y<1000 or x>=9000 or y>=9000: return False
        return not (4000<=x<6000 and 3000<=y<7000)   # a lake 2000 x 4000 between start and target
syn=Syn(real.mp)
for tgt in [(7000,5000),(7000,5600),(7500,4000)]:
    s=(3000,5000)
    for sp in (32,45):
        out=[]
        for h in (1,-1):
            r=follow.run(syn,s,tgt,sp,'bug2',h,a0=16,turn=16)
            out.append((r['ok'],round(r['length'])))
        print('target',tgt,'speed',sp,'L,R:',out)
