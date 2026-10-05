import rec, sys
def tl(path, i, f0=4195, f1=99999, cols=None, minrun=1):
    fs=rec.load(path)[1:]
    prev=None;n=0;start=0;out=[]
    for f in fs:
        if f.f<f0 or f.f>f1: continue
        r=f.p2[i]
        if not r[0]: k=None
        else:
            k=(r[2],r[3],r[4],r[5],r[63],r[46],r[54],int(rec.u16(r,10)!=rec.u16(r,14)),rec.s16(r,24))
        if k!=prev:
            if prev is not None or n: out.append((start,n,prev))
            prev=k;n=0;start=f.f
        n+=1
    out.append((start,n,prev))
    return out
if __name__=='__main__':
    for s,n,k in tl(sys.argv[1],int(sys.argv[2]),int(sys.argv[3]) if len(sys.argv)>3 else 4195,int(sys.argv[4]) if len(sys.argv)>4 else 99999):
        print(s,n,k)
