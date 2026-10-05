import rec, collections, sys
def trans(fs, idxs, key=lambda r:(r[2],r[3])):
    T=collections.Counter(); S=collections.Counter()
    for i in idxs:
        prev=None
        for f in fs:
            r=f.p2[i]
            if not r[0] or r[19]!=0: prev=None; continue
            k=key(r)
            S[k]+=1
            if prev is not None and k!=prev: T[(prev,k)]+=1
            prev=k
    return T,S
if __name__=='__main__':
    fs=rec.load(sys.argv[1])[1:]
    T,S=trans(fs,range(13))
    print('state histogram (2,3):'); 
    for k,v in sorted(S.items()): print(k,v)
    print('transitions:')
    for (a,b),v in sorted(T.items()): print(a,'->',b,v)
