"""Differential test of the sprite depth sort $e84c: four (index<<16 | key) registers, key = Y (-3698(A4)[i]) + 255 if bit 0 of -3826(A4)[i]
(car on the elevated level), bubble-sorted ascending by signed-word compare with exg, result = car indices in draw order at -4042(A4)."""
import sys, os, random, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
from calldiff import CallDiff

def model(ys, flags):
    k = [((i << 16) | ((y + (255 if f & 1 else 0)) & 0xFFFF)) for i, (y, f) in enumerate(zip(ys, flags))]
    def s16(v): v &= 0xFFFF; return v - 65536 if v & 0x8000 else v
    while True:
        sw = False
        for a in range(3):
            # cmp.w Da,Da+1 ; bpl -> no swap when (D[a+1].w - D[a].w) >= 0 (signed, flag N clear)
            d = s16(k[a + 1]) - s16(k[a])
            n = ((d & 0xFFFF) >> 15) & 1
            if n:
                k[a], k[a + 1] = k[a + 1], k[a]; sw = True
        if not sw: break
    return [v >> 16 for v in k]

cd = CallDiff()
random.seed(9)
ok = 0; N = int(sys.argv[1]) if len(sys.argv) > 1 else 40
for t in range(N):
    ys = [random.randrange(0, 186) for _ in range(4)]
    if t % 5 == 0: ys[1] = ys[0]                      # ties
    flags = [random.choice([0, 1, 0x400, 0x401]) for _ in range(4)]
    for i in range(4):
        cd.poke_word(A4 - 3698 + 2 * i, ys[i]); cd.poke_word(A4 - 3826 + 2 * i, flags[i])
    oc, ch, d = cd.call(0xE84C)
    assert oc == 'returned', oc
    got = [struct.unpack('>H', bytes(cd.apply(cd.ram[A4 - 4042 + 2 * i:A4 - 4042 + 2 * i + 2], A4 - 4042 + 2 * i, ch)))[0] for i in range(4)]
    want = model(ys, flags)
    ok += (got == want)
    if got != want: print('MISMATCH ys', ys, 'flags', flags, 'got', got, 'want', want)
print('depth sort $e84c: %d / %d random configurations equal' % (ok, N))
cd.close()
