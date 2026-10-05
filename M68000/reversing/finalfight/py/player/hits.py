"""hits.py <log>: list episodes of sub=06 (hit reaction) with the +63 hit type, ss sequence with durations, max y rise, +22 attacker id, hp delta."""
import sys
rows=[]
for l in open(sys.argv[1]):
    if l[0] in "EQC": continue
    p=l.split(); d={'rel':int(p[1])}
    for t in p[2:]:
        k,v=t.split('=',1); d[k]=v
    rows.append(d)
i=0
while i<len(rows):
    r=rows[i]
    if r['st']=='02' and r['sub']=='06' and (i==0 or rows[i-1]['sub']!='06'):
        j=i
        while j<len(rows) and rows[j]['st']=='02' and rows[j]['sub']=='06': j+=1
        seq=[]; 
        for k in range(i,j):
            key=(rows[k]['ss'],rows[k]['s5'])
            if seq and seq[-1][0]==key: seq[-1][1]+=1
            else: seq.append([key,1])
        gy=int(rows[i]['gy'],16); ymax=max(int(rows[k]['y'],16) for k in range(i,j))
        prev=rows[i-1] if i else r
        nxt=rows[j] if j<len(rows) else r
        print('rel %5d-%5d n=%3d type63=%s id22=%s ss/s5 seq=%s ymax-gy=%d hp %s->%s next st/sub=%s/%s prev sub=%s in=%s'%(r['rel'],rows[j-1]['rel'],j-i,rows[i]['b63'],rows[i]['b22'],' '.join('%s/%s:%d'%(a[0][0],a[0][1],a[1]) for a in seq),ymax-gy,prev['hp'][:4],rows[j-1]['hp'][:4],nxt['st'],nxt['sub'],prev['sub'],r['in']))
        i=j
    else: i+=1
