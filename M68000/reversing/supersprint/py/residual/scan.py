"""Static coverage of the 10000-byte sound script area: which byte ranges are reached from the known starters, and what lies between."""
import sys, os, struct
HERE = os.path.dirname(os.path.abspath(__file__))
d = HERE
while not os.path.exists(os.path.join(d, 'reversing', 'supersprint', 'py', 'sscfg.py')):
    d = os.path.dirname(d)
sys.path.insert(0, os.path.join(d, 'reversing', 'supersprint', 'py')); import sscfg
dat = open(os.path.join(sscfg.FILES, 'SUPER.DAT'), 'rb').read()
S = dat[198966 + 3684:198966 + 3684 + 10000]
W = lambda p: struct.unpack_from('>h', S, p)[0]
STARTS = [0,14,28,74,88,166,180,194,208,222,236,242,272,302,316,322,336,906,2580,3398,4488,5302,5916,6794,7780]

def stream(off):
    p = off
    while True:
        op = W(p); p += 2
        if op < 7: p += 2
        else: return p
cov = {}
for s in STARTS:
    e = stream(s); cov[s] = e
prev = 0
for s in sorted(cov):
    e = cov[s]
    gap = s - prev
    print('start %5d end %5d len %5d%s' % (s, e, e - s, ('   GAP before: %d bytes' % gap) if gap else ''))
    prev = max(prev, e)
print('last end', prev, 'remaining bytes to 10000:', 10000 - prev)
nz = [i for i in range(prev, 10000) if S[i]]
print('nonzero bytes after last end:', len(nz), nz[:5], nz[-5:] if nz else '')
