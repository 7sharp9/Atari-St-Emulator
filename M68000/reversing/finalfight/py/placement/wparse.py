import re,sys,collections
def load(path):
    ev=[]
    for line in open(path):
        p=line.split()
        if p[0]!='W': continue
        ev.append(dict(f=int(p[1]),pool=p[2],idx=int(p[3]),addr=int(p[4],16),pc=int(p[5][3:],16),off=int(p[6][4:]),m=int(p[7][2:],16),d=int(p[8][2:],16)))
    return ev
if __name__=='__main__':
    ev=load(sys.argv[1])
    c=collections.Counter()
    for e in ev:
        if e['off']==0 and e['f']>100: c[(e['pool'],'%06x'%e['pc'],'m%04x'%e['m'],'d%04x'%e['d'])]+=1
    for k,v in sorted(c.items()): print(v,*k)
