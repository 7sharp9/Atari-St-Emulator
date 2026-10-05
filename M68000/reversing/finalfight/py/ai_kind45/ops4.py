"""ops4.py <trace> <rec>: kind 4 attack-script statistics: script ids picked ($31870 sets 150(A6) and 146(A6)), ops executed (151(A6) when 4(A6)=6),
attack boxes (+45) seen, Cody health drops (frame, amount, attack box, op)."""
import sys, collections
from fr import *
path=sys.argv[1]; r=int(sys.argv[2],16)
ids=collections.Counter(); ops=collections.Counter(); boxes=collections.Counter(); hits=[]
st=collections.Counter(); prev=None; prevcody=None; last=None
for f,buf in frames(path):
    s=(b(buf,r),b(buf,r+2),b(buf,r+3),b(buf,r+4),b(buf,r+5))
    if s[0]==0: continue
    st[(s[1],s[2])]+=1
    if prev and prev[2]==4 and prev[3]!=2 and s[2]==4 and s[3]==2 and prev[1]==2: ids[b(buf,r+150)]+=1
    if prev and not (prev[2]==4 and prev[3]==6 and prev[4]==0) and s[2]==4 and s[3]==6 and s[4]==0 : ops[b(buf,r+151)]+=1
    a=b(buf,r+45)
    if a and (not prev or True): boxes[a]+=0
    ch=w(buf,0xff8580)
    if prevcody is not None and ch<prevcody and ch!=0 and prevcody-ch<200: hits.append((f,prevcody-ch,b(buf,r+45),b(buf,r+151),s[1:]))
    prevcody=ch
    prev=s
print('script ids picked',dict(sorted(ids.items())))
print('ops started',dict(sorted(ops.items())))
print('(s2,s3) frames',dict(sorted(st.items())))
print('cody hits',len(hits)); 
for h in hits: print('  frame %d dmg %d box45=%02x op151=%02x state=%s'%h)
