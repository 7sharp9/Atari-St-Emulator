import pickle,statistics,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import follow
from collections import defaultdict
d=pickle.load(open(follow.DATA/'pairs.pkl','rb')); P=d['pairs']
R=pickle.load(open(follow.DATA/'results.pkl','rb'))
b={i:r for i,r in R.items() if r['cls']=='b'}
u=set((P[i]['plane'],P[i]['x'],P[i]['y'],P[i]['tx'],P[i]['ty'],P[i]['speed']) for i in b)
men=set((P[i]['series'],P[i]['obj']) for i in b)
print('b records',len(b),'unique (start,target,speed)',len(u),'men',len(men))
def stat(names):
    per=defaultdict(list)
    for i,r in b.items():
        ok=[r['algos'][n] for n in names if r['algos'][n]['ok']]
        if ok: per[(P[i]['series'],P[i]['obj'])].append(min(c['length'] for c in ok)/r['astar']['len'])
    m=[statistics.median(v) for v in per.values()]
    return len(per),statistics.median(m),sorted(m)[int(.9*len(m))],max(m)
for names in (['bug2_L'],['bug2_R'],['bug2_L','bug2_R'],['kcd_L','kcd_R'],['kclear_L','kclear_R']):
    print(names,'men with a solved pair, median-of-man-medians %.2f p90 %.2f worst %.2f'%stat(names)[1:], stat(names)[0])
# unique-pair-level
seen={}
for i,r in b.items():
    k=(P[i]['plane'],P[i]['x'],P[i]['y'],P[i]['tx'],P[i]['ty'],P[i]['speed']); seen[k]=r
for names in (['bug2_L'],['bug2_R'],['bug2_L','bug2_R'],['kcd_L','kcd_R']):
    ok=0; rat=[]
    for r in seen.values():
        o=[r['algos'][n] for n in names if r['algos'][n]['ok']]
        if o: ok+=1; rat.append(min(c['length'] for c in o)/r['astar']['len'])
    rat.sort()
    print('unique',names,ok,'/',len(seen),'median %.2f p90 %.2f worst %.2f'%(statistics.median(rat),rat[int(.9*len(rat))],rat[-1]))
# length in ticks terms: bug2 best vs astar over speed
rs=[min(r['algos'][n]['length'] for n in ('bug2_L','bug2_R') if r['algos'][n]['ok'])/r['astar']['len'] for r in b.values()]
print('worst best-of-both pair ratio', max(rs))
# ratio vs straight-line
