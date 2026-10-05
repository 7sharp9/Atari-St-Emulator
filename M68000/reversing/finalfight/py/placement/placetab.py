# parse the placement tables of $6026: initial lists ($636e) and the trigger lists ($6346 live, $631e other)
from rom import *
NAMES={0:'none',2:'tag2 fighter',4:'tag4',6:'tag6 weapon',8:'tag8',10:'tag a prop',12:'slot ffb228',14:'none7',16:'slot ffb1e8',18:'tag12 item',20:'tag14'}
def areas(base,nstage=10):
    out={}
    for s in range(nstage):
        P=l(base+4*s)
        nxt=sorted(set(l(base+4*t) for t in range(nstage) if l(base+4*t)>P)|{P+0x1000})[0]
        # area table: words offsets from P; count = first offset/2
        first=w(P)
        n=first//2
        out[s]=[(P+w(P+2*a)) for a in range(n)]
    return out
def entry(a):
    return dict(addr=a,trig=w(a),x=w(a+2),y=w(a+4),sp=b(a+6),kind=b(a+7),c20=b(a+8),c21=b(a+9),f54=b(a+10),f98=b(a+11),lvl=b(a+12),p2=b(a+13))
def initlist(a):
    r=[]
    while not (w(a)&0x8000):
        r.append(entry(a)); a+=14
    return r
def trigmodes(a):
    # state 2 list: first word = mode; then entries, 0x8000 + word = mode change, other negative = end
    mode=w(a); a+=2
    segs=[]
    cur=[mode,[]]
    while True:
        t=w(a)
        if t&0x8000:
            if t==0x8000:
                mode=w(a+2); a+=4
                segs.append(cur); cur=[mode,[]]
                continue
            else:
                end=a; break
        cur[1].append(entry(a)); a+=14
    segs.append(cur)
    return segs,end
if __name__=='__main__':
    import sys
    A0=areas(0x636e); A1=areas(0x6346); A2=areas(0x631e)
    for s in range(6):
        print('stage',s,'init areas',[hex(x) for x in A0[s]],'trig',[hex(x) for x in A1[s]])
