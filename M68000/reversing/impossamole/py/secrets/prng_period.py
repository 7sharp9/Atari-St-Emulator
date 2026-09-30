"""Structure of PRNG A ($bef4) with the four counters frozen: is s -> f(s) a bijection on 16 bits, how long are its cycles; and the joint period of the counters."""
import sys
sys.path.insert(0, __file__.rsplit('/', 1)[0])
from prng import bef4
def analyse(c, x=0):
    f = [bef4(s, *c, x) for s in range(65536)]
    img = len(set(f))
    seen = [0] * 65536; cyc = []
    for s in range(65536):
        if seen[s]: continue
        path = []; t = s
        while not seen[t]:
            seen[t] = 1; path.append(t); t = f[t]
        # t is either on this path (new cycle) or visited earlier
        if t in path:
            cyc.append(len(path) - path.index(t))
    return img, sorted(cyc, reverse=True)[:6], len(cyc)
for c in [(0, 0, 0, 0), (1, 2, 3, 4), (100, 200, 300, 400), (0x1234, 0x2468, 0x369c, 0x48d0)]:
    img, top, n = analyse(c)
    print('counters', c, ': distinct images', img, '/ 65536; cycles', n, 'longest', top)
# counters: each is a 16-bit wrap of (k * frames): period in VBLs
print('counter c1 (+1) wraps every 65536 VBLs, c2 (+2) every 32768, c3 (+3) every 65536, c4 (+4) every 16384: joint period of the counter vector = 65536 VBLs')
