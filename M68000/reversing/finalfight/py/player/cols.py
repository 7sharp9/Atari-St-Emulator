"""cols.py <log> <relLo> <relHi> <step> col,col,...   print selected columns of a pdrive log"""
import sys
lo,hi,step=int(sys.argv[2]),int(sys.argv[3]),int(sys.argv[4]); cols=sys.argv[5].split(',')
for l in open(sys.argv[1]):
    if l[0] in "EQC": continue
    p=l.split(); rel=int(p[1])
    if rel<lo or rel>hi or (rel-lo)%step: continue
    d={'f':p[0],'rel':p[1]}
    for t in p[2:]:
        k,v=t.split('=',1); d[k]=v
    print(' '.join('%s=%s'%(c,d.get(c,'?')) for c in ['rel']+cols))
