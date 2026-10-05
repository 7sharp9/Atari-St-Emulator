import rec, collections, sys
def hit_entries(fs):
    out=[]
    for i in range(13):
        prev=None
        for fi,f in enumerate(fs):
            r=f.p2[i]
            if not r[0] or r[19]!=0: prev=None; continue
            k=(r[2],r[3])
            if k==(2,4) and prev!=(2,4):
                # first frame where 4(A6)!=0 (dispatcher ran)
                rr=r
                for fj in range(fi,min(fi+4,len(fs))):
                    rr=fs[fj].p2[i]
                    if rr[4]!=0: break
                air = rec.u16(r,10)!=rec.u16(r,14)
                out.append(dict(frame=f.f,i=i,ch=r[20],t63=r[63],first4=rr[4],air=air,hp=rec.s16(r,24),sh=rec.s16(r,26),prev=prev,a22=r[22]))
            prev=k
    return out
if __name__=='__main__':
    C=collections.Counter(); P=collections.Counter()
    for fn in sys.argv[1:]:
        fs=rec.load(fn)[1:]
        for h in hit_entries(fs):
            C[(h['t63'],h['first4'],h['air'])]+=1; P[h['prev']]+=1
    print('(63 type, first 4(A6), airborne) -> count')
    for k,v in sorted(C.items()): print(k,v)
    print('previous (2,3) state at hit entry',dict(P))
