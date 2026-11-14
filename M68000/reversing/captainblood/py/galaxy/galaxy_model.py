"""galaxy_model.py <arm.txt> [--break NAME] : model of TOS 1.00 XBIOS Random ($fc132c) and Captain Blood's galaxy placer ($b830),
seeded from the hz200 count at the first call, gated against the 128 planet words dumped from an arm's REPL output (diffarms.parse).
--break mul|add|shift|y|dup|seed : change one constant of the model (broken-model control)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from diffarms import parse
class Rnd:
    def __init__(s, hz200, mul=0xbb40e62d, add=1, sh=8):
        s.seed = 0; s.hz = hz200; s.mul = mul; s.add = add; s.sh = sh
    def __call__(s):
        if s.seed == 0: s.seed = ((s.hz << 16) | (s.hz & 0xffffffff)) & 0xffffffff   # asl.l #16 / or.l $4ba
        s.seed = (s.seed * s.mul + s.add) & 0xffffffff
        return (s.seed >> s.sh) & 0xffffff
BREAKS = ('mul', 'add', 'shift', 'y', 'dup', 'seed')
def galaxy(hz200, brk=None):
    if brk is not None and brk not in BREAKS: raise ValueError('unknown break %r' % brk)
    kw = {}
    if brk == 'mul': kw['mul'] = 0xbb40e62c
    if brk == 'add': kw['add'] = 2
    if brk == 'shift': kw['sh'] = 9
    hz = hz200 + (1 if brk == 'seed' else 0)
    r = Rnd(hz, **kw); ylo = 0x800 if brk != 'y' else 0x900
    tab = {}
    d0 = r(); tab[127] = (d0 & 0xff00) | ((d0 & 0xff) >> 1)
    rejects = 0
    for i in range(126, -1, -1):
        while True:
            if rejects > 100000: return tab, rejects   # broken-model guard
            w = (r() & 0xffff) >> 1
            if (w & 0xff) <= 8 or (w & 0xff) > 0xf6 or w <= ylo or w > 0x78ff: rejects += 1; continue
            if brk != 'dup' and any(tab[j] == w for j in range(i + 1, 128)): rejects += 1; continue
            break
        tab[i] = w
    return tab, rejects
if __name__ == '__main__':
    t, pos, seed, hz = parse(sys.argv[1])
    brk = None
    if len(sys.argv) > 2:
        if sys.argv[2] != '--break' or len(sys.argv) != 4: sys.exit('usage: galaxy_model.py <arm.txt> [--break %s]' % '|'.join(BREAKS))
        brk = sys.argv[3]
        if brk not in BREAKS: sys.exit('unknown --break %r (choose %s)' % (brk, ', '.join(BREAKS)))
    m, rej = galaxy(hz, brk)
    ok = sum(i in m and m[i] == int.from_bytes(t[4*i:4*i+2], 'big') for i in range(128))
    print('hz200=%d model==RAM position words: %d/128 (rejected draws %d) break=%s' % (hz, ok, rej, brk))
