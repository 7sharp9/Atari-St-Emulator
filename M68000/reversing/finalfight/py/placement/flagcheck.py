# flagcheck.py <tap log> <bp log> : kind 1 pool-8 tile patches. A write of 1 to the flag array $ff12de+ch (tap) against the patch routine call ($4840/$4872/... breakpoints) of the record with +20 = ch
import sys,re
sets=[]
for l in open(sys.argv[1]):
    p=l.split()
    if p[0]!='T': continue
    a=int(p[3][2:],16); m=int(p[4][2:],16); d=int(p[5][2:],16)
    if 0xff12de<=a<=0xff12ef and int(p[1])>1400:
        hi=(d>>8)&0xff; lo=d&0xff
        if m&0xff00 and hi==1: sets.append((int(p[1]),a-0xff12de,p[2]))
        if m&0x00ff and lo==1: sets.append((int(p[1]),a-0xff12de+1,p[2]))
patches=[]
for l in open(sys.argv[2]):
    m=re.match(r'(\d+) B (\w+) A6=(\w+) ch=(\w+)',l)
    if m: patches.append((int(m.group(1)),int(m.group(4),16),m.group(2)))
ok=0
for f,ch,pc in sets:
    p=[x for x in patches if x[1]==ch and f<=x[0]<=f+12]
    print('flag %2d set at frame %5d by %s -> patch %s'%(ch,f,pc,('at frame %d (%s +%d)'%(p[0][0],p[0][2],p[0][0]-f)) if p else 'NONE'))
    ok+= bool(p)
print('%d of %d flag writes followed by their patch within 12 frames; %d patch calls in total'%(ok,len(sets),len(patches)))
