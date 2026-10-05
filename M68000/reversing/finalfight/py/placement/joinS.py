# join S lines (first sighting of a live record) with the write that created it (+0 byte set to 1)
import sys,re,collections
from wparse import load
def loadS(path):
    out=[]
    for line in open(path):
        if not line.startswith('S '): continue
        m=re.match(r'S (\d+) pool=(\S+) rec=(\d+) (\w+) kind=(\w+) ch=(\w+) ent=(\w+) lvl=(\w+) x=(\w+) y=(\w+) hp=(\w+) cam=(\w+) scr=(\w+)',line)
        g=m.groups()
        out.append(dict(f=int(g[0]),pool=g[1],idx=int(g[2]),addr=int(g[3],16),kind=int(g[4],16),c20=int(g[5],16),c21=int(g[6],16),lvl=int(g[7],16),x=int(g[8],16),y=int(g[9],16),hp=int(g[10],16),cam=int(g[11],16),scr=int(g[12],16)))
    return out
def spawns(ev):
    sp=[]
    for e in ev:
        if e['off']==0 and e['m']&0xff00 and (e['d']>>8)==1 and e['f']>100:
            sp.append(e)
    return sp
def join(logS,wpath):
    ev=load(wpath); sp=spawns(ev)
    by=collections.defaultdict(list)
    for e in sp: by[(e['pool'],e['idx'])].append(e)
    res=[]
    for s in loadS(logS):
        cand=[e for e in by[(s['pool'],s['idx'])] if 0<=s['f']-e['f']<=1]
        s['pc']=cand[0]['pc'] if cand else None
        res.append(s)
    return res
if __name__=='__main__':
    res=join(sys.argv[1],sys.argv[2])
    for s in res:
        print('f=%5d pool=%-2s rec=%2d kind=%02x +20=%02x +21=%02x lvl=%02x x=%04x y=%04x cam=%04x scr=%06x pc=%s'%(s['f'],s['pool'],s['idx'],s['kind'],s['c20'],s['c21'],s['lvl'],s['x'],s['y'],s['cam'],s['scr'],('%06x'%s['pc']) if s['pc'] else '??????'))
