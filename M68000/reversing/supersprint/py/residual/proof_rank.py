"""$13b34 (race leader key) vs Python: key[c] = (lap[c] * $2000 + a[c] * $400 + b[c]) & $FFFF with lap = -3906(A4)[c], a = -3850(A4)[c], b = -3842(A4)[c];
returns the index (low word of D0) of the first maximum under an unsigned compare chain 0 < 1 < 2 < 3 (a later car wins only if STRICTLY greater), key in the high word.
Differential vs callcap, random state incl. 16-bit wrap.  usage: proof_rank.py [trials]"""
import sys, os, random, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rcommon import *
os.environ['ENGINE_OUT'] = os.path.join(AGENT, 'engine_out')
from common import *
from calldiff import CallDiff
N = int(sys.argv[1]) if len(sys.argv) > 1 else 60
def leader(lap, a, b):
    key = [((lap[c] << 13) + (a[c] << 10) + b[c]) & 0xFFFF for c in range(4)]
    best = 0
    for c in (1, 2, 3):
        if key[best] < key[c]: best = c
    return best, key[best]
cd = CallDiff(); random.seed(8); ok = 0
for t in range(N):
    lap = [random.randrange(0, 6) for _ in range(4)]; a = [random.randrange(0, 8) for _ in range(4)]; b = [random.randrange(0, 120) for _ in range(4)]
    if t % 5 == 0: lap = [random.choice([0, 1, 9]) for _ in range(4)]            # includes wrap (9 * $2000 overflows 16 bits)
    if t % 7 == 0: lap = [2] * 4; a = [1] * 4; b = [5, 5, 5, 5]                  # all equal: car 0
    for c in range(4):
        cd.poke_word(A4 - 3906 + 2 * c, lap[c]); cd.poke_word(A4 - 3850 + 2 * c, a[c]); cd.poke_word(A4 - 3842 + 2 * c, b[c])
    oc, ch, d = cd.call(0x13B34, presets='A5=a304 A4=1eb44')
    assert oc == 'returned', oc
    d0 = d['regN'][0]
    idx, key = leader(lap, a, b)
    ok += ((d0 & 0xFFFF) == idx and (d0 >> 16) == key)
    if not ((d0 & 0xFFFF) == idx and (d0 >> 16) == key): print('  mismatch', lap, a, b, 'live idx %d key %d' % (d0 & 0xFFFF, d0 >> 16), 'model', idx, key)
print('$13b34 leader/rank key: %d / %d trials equal' % (ok, N))
cd.close()
