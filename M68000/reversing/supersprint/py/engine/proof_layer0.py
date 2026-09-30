"""$154d2(screen): builds the depth layer 0 bitmap (-94(A4), 8000 B, 1 bpp, 40 B/row) from a rendered screen: bit = 1 unless the pixel's colour
index is 3, 4 or 7.  Differential test on random screens (random planar noise and the real stash)."""
import sys, os, struct, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
from calldiff import CallDiff

cd = CallDiff(); R = cd.ram
lay = struct.unpack_from('>I', R, A4 - 94)[0]
stash = struct.unpack_from('>I', R, A4 - 86)[0]
SRC = 0x72000
random.seed(8)
def model(scr):
    out = bytearray(8000)
    for y in range(200):
        for xw in range(0, 320, 16):
            o = y * 160 + (xw >> 4) * 8
            pl = [(scr[o + 2 * p] << 8) | scr[o + 2 * p + 1] for p in range(4)]
            bits = 0
            for b in range(16):
                c = sum(((pl[p] >> (15 - b)) & 1) << p for p in range(4))
                bits = (bits << 1) | (0 if c in (3, 4, 7) else 1)
            out[y * 40 + (xw >> 4) * 2] = bits >> 8; out[y * 40 + (xw >> 4) * 2 + 1] = bits & 255
    return bytes(out)
ok = tot = 0
for t in range(4):
    data = bytes(R[stash:stash + 32000]) if t == 0 else bytes(random.getrandbits(8) for _ in range(32000))
    cd.poke(SRC, data)
    oc, ch, d = cd.call(0x154D2, struct.pack('>I', SRC), maxsteps=4000000)
    assert oc == 'returned', oc
    live = cd.apply(R[lay:lay + 8000], lay, ch)
    mine = model(data)
    e = sum(1 for a, b in zip(live, mine) if a == b); ok += e; tot += 8000
    print('screen %s: layer-0 bytes equal %d / 8000' % ('stash' if t == 0 else 'noise%d' % t, e))
print('TOTAL %d / %d' % (ok, tot))
cd.close()
