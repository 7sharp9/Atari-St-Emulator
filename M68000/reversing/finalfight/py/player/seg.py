"""Summarise a pdrive log into segments of constant (st,sub,ss,s5,m66): frames, input byte, b44/b45/b54 sets, x/y deltas, hp."""
import sys,re
rows=[]
for l in open(sys.argv[1]):
    if l[0] in "EQC": continue
    p=l.split(); d={'f':int(p[0]),'rel':int(p[1])}
    for t in p[2:]:
        k,v=t.split('=')
        d[k]=v
    rows.append(d)
keys=sys.argv[2].split(',') if len(sys.argv)>2 else ['st','sub','ss','s5','m66']
seg=None; out=[]
for r in rows:
    k=tuple(r[x] for x in keys)
    if seg and seg['k']==k: seg['rows'].append(r)
    else:
        seg={'k':k,'rows':[r]}; out.append(seg)
for s in out:
    r0,r1=s['rows'][0],s['rows'][-1]
    ins=sorted(set(r['in'] for r in s['rows']))
    b45=sorted(set(r['b45'] for r in s['rows'])); b44=sorted(set(r['b44'] for r in s['rows']))
    b54=sorted(set(r['b54'] for r in s['rows']))
    print('rel %4d-%4d n=%3d %s in=%s b44=%s b45=%s b54=%s x %s>%s y %s>%s hp %s>%s b22=%s b63=%s'%(r0['rel'],r1['rel'],len(s['rows']),'/'.join(f'{a}={b}' for a,b in zip(keys,s['k'])),','.join(ins),','.join(b44),','.join(b45),','.join(b54),r0['x'],r1['x'],r0['y'],r1['y'],r0['hp'][:4],r1['hp'][:4],r1['b22'],r1['b63']))
