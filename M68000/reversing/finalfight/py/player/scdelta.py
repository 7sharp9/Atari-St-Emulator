"""scdelta.py <log>: score changes (+132/+134 BCD) with Cody's attack-box id (+45), +22 attacker id of the victim not available here: print frame, delta, b45, sub/ss"""
import sys
prev=None
for l in open(sys.argv[1]):
    if l[0] in 'EQ': continue
    p=l.split(); r={t.split('=')[0]:t.split('=')[1] for t in p[2:] if '=' in t}
    sc=int(r['scH']+r['sc'],16)
    def bcd(v): return int(('%08x'%v))
    if prev is not None and sc!=prev: print('rel %4s score %d -> %d (+%d)  b45=%s sub=%s ss=%s'%(p[1],bcd(prev),bcd(sc),bcd(sc)-bcd(prev),r['b45'],r['sub'],r['ss']))
    prev=sc
