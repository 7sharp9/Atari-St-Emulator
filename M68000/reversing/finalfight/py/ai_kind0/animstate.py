# which animation thunk (anims.THUNKS) is playing in each (3,4,5[,66]) state: match 32(A6) (anim list pointer) to the thunks' header ranges
import rec, collections, sys, anims as A
ranges=[]
for t,tab in A.THUNKS.items():
    for ch in range(4):
        hdr=tab+A.sw(tab+2*ch); fr=A.anim(hdr)
        ranges.append((hdr,hdr+4*len(fr),t,ch))
def find(ptr,ch):
    for lo,hi,t,c in ranges:
        if c==ch and lo<=ptr<hi: return t
    return None
H=collections.defaultdict(collections.Counter)
for fn in sys.argv[1:]:
    fs=rec.load(fn)[1:]
    for f in fs:
        for r in f.p2:
            if r[0] and r[19]==0 and r[20]<4 and r[2] in (2,4):
                key=(r[2],r[3],r[4] if r[3] in (4,12) else 0)
                H[key][find(rec.u32(r,32),r[20])]+=1
for k in sorted(H): print('2,3,4=',k,{('%x'%t if t else None):v for t,v in H[k].most_common(4)})
