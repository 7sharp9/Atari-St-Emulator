"""Parse depacked BLOOD.COM (usage: blood_com.py depacked/BLOOD.COM). Layout read from the loader code
(zuul image $d96a..$d998, $dbf4): header $20; 120 vocabulary records x16 from $20 (index = 1-based);
race records x32 at $910; B stream at $b10 (len header+4), A stream after it (len header+8)."""
import sys,struct,collections
b=open(sys.argv[1],'rb').read()
lenB,lenA=struct.unpack('>II',b[4:12])
print('size',len(b),'lenB',hex(lenB),'lenA',hex(lenA),'check',0xb10+lenB+lenA==len(b))
vocab=[]
for i in range(120):
    r=b[0x20+16*i:0x30+16*i]; vocab.append((r[0],r[1:].split(b'\0')[0].decode()))
print('vocab',len(vocab),'flag bytes',collections.Counter(hex(f) for f,_ in vocab))
for i,(f,n) in enumerate(vocab,1): print(f"{i:3d} {f:02x} {n}",end=' | ' if i%4 else '\n')
print()
B0=0xb10; A0=B0+lenB
races=[]
for i in range(16):
    r=b[0x910+32*i:0x930+32*i]
    name=r[:16].decode('latin1').strip('\0 ').strip()
    offA,offB=struct.unpack('>II',r[16:24]); la,lb=struct.unpack('>HH',r[24:28]); tail=r[28:32].hex()
    races.append((name,offA,offB,la,lb)); print(i,repr(name),'offA',hex(offA),'offB',hex(offB),'lenA',hex(la),'lenB',hex(lb),tail)
print('contiguous:',all(races[i][1]+races[i][3]==races[i+1][1] and races[i][2]+races[i][4]==races[i+1][2] for i in range(15)),'sum',hex(races[15][1]+races[15][3]),hex(races[15][2]+races[15][4]))
# stream A of each race: records [hdr][flag][n payload]
for i,(name,oa,ob,la,lb) in enumerate(races[:8]):
    s=b[A0+oa:A0+oa+la]; p=0; recs=collections.Counter(); n=0; end=None
    while p<len(s):
        h=s[p]
        if h==0xff: end=p; break
        L=h&0x1f; recs[h&0xe0]+=1; p+=2+L; n+=1
    print(i,name,'A records',n,'by hdr flags',{hex(k):v for k,v in sorted(recs.items())},'ends at',end,'of',la)
