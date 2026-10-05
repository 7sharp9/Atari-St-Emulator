# match.py <bp log> <S log (early census)> <W log> : every placement entry the spawner $61a8 was called for (breakpoint after the call: $6072 init lists, $60da trigger lists, A3 = the entry)
# against the record first seen live (S line, same pool, kind, +20, +21, x, y, level) and the write that created it (pc $61f8 in the W log).
import sys,re,collections
from rom import *
from placetab import entry,NAMES
from joinS import loadS,load,spawns
POOL={2:'2',4:'4',6:'6',8:'8',10:'a',12:'c',18:'12',20:'14'}
bp=[l.split() for l in open(sys.argv[1]) if ' B ' in l]
S=loadS(sys.argv[2]); ev=load(sys.argv[3]); sp=[e for e in spawns(ev) if e['pc']==0x61f8]
rank=None
# rank (168(A5)) per frame from the bp log (61ec lines carry rank=)
caps={}
for p in bp:
    if p[2]=='61ec': 
        caps[int(p[0])]=caps.get(int(p[0]),[])+[p]
entries=[]
for p in bp:
    if p[2] in ('6072','60da'):
        a=int(p[3][3:],16); e=entry(a); e['f']=int(p[0]); e['list']='init' if p[2]=='6072' else 'trig'; entries.append(e)
used=set(); res=collections.Counter(); out=[]
for e in entries:
    pool=POOL.get(e['sp'])
    if pool is None: res['no spawner (sp %d)'%e['sp']]+=1; out.append((e,None,'no spawner')); continue
    cand=[s for s in S if s['pool']==pool and e['f']<=s['f']<=e['f']+1 and s['kind']==e['kind'] and s['c20']==e['c20'] and s['c21']==e['c21'] and id(s) not in used
          and (e['x']&0x8000 or s['x']==e['x']) and (e['y']&0x8000 or s['y']==e['y'])]
    # pool 'c' / slot records and short-lived records are not in S
    if cand:
        s=cand[0]; used.add(id(s)); res['matched (spawned, fields equal)']+=1; out.append((e,s,'matched'))
        # level check: entry byte ff means 169(A5) (rank); else equal
        if e['lvl']!=0xff and s['lvl']!=e['lvl']: res['  level differs']+=1
    else:
        blocked=[c for c in caps.get(e['f'],[]) if c[3].startswith('D0=1')]
        if pool=='2' and blocked: res['blocked by the spawn gate $3e88 (D0=1)']+=1; out.append((e,None,'blocked $3e88'))
        else: res['unmatched']+=1; out.append((e,None,'UNMATCHED'))
print(dict(res))
for e,s,k in out:
    print('%5d %-4s %06x sp=%-2d kind=%02x +20=%02x +21=%02x x=%04x y=%04x lvl=%02x p2=%02x -> %s %s'%(e['f'],e['list'],e['addr'],e['sp'],e['kind'],e['c20'],e['c21'],e['x'],e['y'],e['lvl'],e['p2'],k,
        ('rec %s%d f=%d'%(s['pool'],s['idx'],s['f'])) if s else ''))
# S lines (from frame 1316 on) not explained by an entry
mine=[s for s in S if id(s) not in used and s['f']>=1316]
pcs={}
for e in sp: pcs[(e['pool'],e['idx'],e['f'])]=e['pc']
print('S lines not from a placement entry:',len(mine))
