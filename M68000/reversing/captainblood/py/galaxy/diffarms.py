"""diffarms.py [arms dir] [ref arm]: parse each arm's REPL dump (arm.sh output; default scratchpad/captainblood/galaxy/arms,
reference arm ctl1), print seed/hz200/start and per-arm diff against the reference (planets differing in position, status
word, status byte). Files with no `PC:` line (not an arm dump) are skipped."""
import sys, glob, os
def root():
    d = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(d, 'tools', 'rdis.py')) and d != os.path.dirname(d): d = os.path.dirname(d)
    return d
ARMS = os.path.join(root(), 'scratchpad', 'captainblood', 'galaxy', 'arms')
def parse(p):
    L=[l.strip() for l in open(p) if l.strip()]
    i=max(k for k,l in enumerate(L) if l.startswith('PC:'))
    hexl=[l for l in L[i+1:] if all(len(t)==2 and all(c in '0123456789abcdef' for c in t) for t in l.split())]
    tab=bytes.fromhex(hexl[0].replace(' ','')); assert len(tab)==512,len(tab)
    pos=bytes.fromhex(hexl[1].replace(' ','')); seed=int(hexl[2].replace(' ',''),16); hz=int(hexl[3].replace(' ',''),16)
    return tab,pos,seed,hz
def ent(tab,i): return tab[4*i:4*i+4]
def is_arm(p):
    return any(l.startswith('PC:') for l in open(p, errors='replace'))
def main(d=ARMS,ref='ctl1'):
    arms={os.path.basename(p)[:-4]:parse(p) for p in sorted(glob.glob(d+'/*.txt')) if is_arm(p)}
    rt=arms[ref][0]
    print('%-10s %10s %8s %6s %s'%('arm','seed','hz200','start','diff vs '+ref+': planets(pos y/x), status-word, byte3'))
    for n,(t,pos,seed,hz) in arms.items():
        dpos=sum(ent(t,i)[:2]!=ent(rt,i)[:2] for i in range(128))
        dst2=sum(ent(t,i)[2]!=ent(rt,i)[2] for i in range(128))
        dst3=sum(ent(t,i)[3]!=ent(rt,i)[3] for i in range(128))
        print('%-10s %10x %8d %6s %d/128 %d/128 %d/128'%(n,seed,hz,pos.hex(),dpos,dst2,dst3))
if __name__=='__main__': main(*(sys.argv[1:3]))
