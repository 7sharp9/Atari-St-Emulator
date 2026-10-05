"""hitlog.py <log> [idx]: damage events on enemy record idx (default 11) with Cody's state at that frame.
prints: rel  hp delta  victim +22 (attack id) +63 (hit type)  Cody sub/ss/s5 and b45 (attack box), in byte, facing"""
import sys
idx=int(sys.argv[2]) if len(sys.argv)>2 else 11
cody={}; ev=[]; prev=None
for l in open(sys.argv[1]):
    p=l.split()
    if p[0]=='E':
        d={t.split('=')[0]:t.split('=')[1] for t in p[3:]}
        if int(d['i'])!=idx: continue
        hp=int(d['hp'],16)
        if hp>=0x8000: hp-=0x10000
        rel=int(p[2])
        if prev is not None and hp!=prev:
            c=cody.get(rel,{})
            ev.append((rel,hp-prev,d['b22'],d['b63'],c.get('sub'),c.get('ss'),c.get('s5'),c.get('b45'),c.get('b44'),c.get('in'),c.get('b46')))
        prev=hp
    elif p[0][0].isdigit():
        d={t.split('=')[0]:t.split('=')[1] for t in p[2:] if '=' in t}
        cody[int(p[1])]=d
for e in ev: print('rel %4d dhp %4d id22=%s type63=%s | Cody sub=%s ss=%s s5=%s b45=%s b44=%s in=%s face=%s'%e)
