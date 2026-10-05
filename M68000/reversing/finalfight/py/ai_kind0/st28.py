import rec, sys
for fn in sys.argv[1:]:
    fs=rec.load(fn)[1:]
    for i in range(13):
        prev=None
        for fi,f in enumerate(fs):
            r=f.p2[i]
            if r[0] and r[19]==0 and r[3]==28 and (prev is None or prev[3]!=28):
                pa=rec.u16(r,102); pi=(pa-0xb2e8)//192 if pa else None
                seq=[]
                for fj in range(fi,min(fi+80,len(fs))):
                    rr=fs[fj].p2[i]
                    if not(rr[0] and rr[19]==0): break
                    pr=fs[fj].props[pi] if pi is not None else None
                    seq.append((fs[fj].f,rr[3],rr[4],rr[45],rr[23],(pr[0],rec.s16(pr,24),pr[19],pr[105],pr[23]) if pr else None))
                comp=[seq[0]]+[s for a,s in zip(seq,seq[1:]) if s[1:]!=a[1:]]
                print(fn,'rec',i,'state28 from',f.f,'prop idx',pi,'(frame,3,4,45,23,(prop in-use,hp,kind,105,23))'); 
                for c in comp[:8]: print('   ',c)
            prev=r if r[0] else None
