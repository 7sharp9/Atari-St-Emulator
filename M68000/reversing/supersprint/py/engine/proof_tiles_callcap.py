"""Full-screen differential test of the tile-map renderer $152d2(map, dst) against tiles.py for all 11 maps (32000 bytes each), and of the
word-RLE unpacker $1484a(src, dst) on the two RLE blocks resident in RAM (B12 credits picture at -126(A4), B1 ready-screen cars at -102(A4))."""
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
from calldiff import CallDiff
from tiles import TilePack, render_map
import rle

dat = open(os.path.join(sscfg.FILES, 'SUPER.DAT'), 'rb').read()
pack = TilePack(dat[52566:52566 + 80000])
cd = CallDiff(); R = cd.ram
DST = 0x72000           # free RAM above the pool
tot = ok = 0
for m in range(11):
    cd.poke(DST, bytes(32000) if m == 0 else bytes(32000))    # start from a clean buffer each time (copy words reference earlier tiles)
    oc, ch, d = cd.call(0x152D2, struct.pack('>HI', m, DST), maxsteps=6000000)
    assert oc == 'returned', oc
    live = cd.apply(bytes(32000), DST, ch)
    mine = bytes(render_map(pack, m))
    eq = sum(1 for a, b in zip(live, mine) if a == b)
    ok += eq; tot += 32000
    print('map %2d: $152d2 vs tiles.py screen bytes equal %d / 32000' % (m, eq))
print('TILE MAPS TOTAL %d / %d' % (ok, tot))
for name, src_off, n in (('B12 credits', A4 - 126, 8000), ('B1 cars', A4 - 102, 9120)):
    src = struct.unpack_from('>I', R, src_off)[0]
    cd.poke(DST, bytes(32000))
    oc, ch, d = cd.call(0x1484A, struct.pack('>II', src, DST), maxsteps=30000000)
    assert oc == 'returned', oc
    live = cd.apply(bytes(32000), DST, ch)
    out, used = rle.unrle_plane_major(rle.to_words(bytes(R[src:src + n]) + b'\0\0'))
    mine = struct.pack('>%dH' % len(out), *out)
    print('$1484a %-12s vs rle.py: %d / 32000 bytes equal (consumed %d words)' % (name, sum(1 for a, b in zip(live, mine) if a == b), used))
cd.close()
