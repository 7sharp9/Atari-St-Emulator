# state histograms over kind-0 record-frames: (2,3) and for 3==12 the 4(A6) sub-state; transitions between (2,3)
import rec, collections, sys
H=collections.Counter(); H12=collections.Counter(); T=collections.Counter(); n=0; held=0
for fn in sys.argv[1:]:
    fs=rec.load(fn)[1:]; n+=len(fs)
    for i in range(13):
        prev=None
        for f in fs:
            r=f.p2[i]
            if not r[0] or r[19]!=0: prev=None; continue
            if r[66]: held+=1
            k=(r[2],r[3]); H[k]+=1
            if k==(2,12): H12[r[4]]+=1
            if prev is not None and prev!=k and not r[66]: T[(prev,k)]+=1
            prev=k
print('frames',n,'kind-0 record-frames',sum(H.values()),'(of which held 66!=0: %d)'%held)
print('(2,3) histogram:',dict(sorted(H.items())))
print('(2,12) by 4(A6):',dict(sorted(H12.items())))
print('transitions (state class,sub): count')
for (a,b),v in sorted(T.items()): print('  ',a,'->',b,v)
