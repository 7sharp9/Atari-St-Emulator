"""Differential tests (callcap vs Python) for the B5 sprite blitters: tree+shadow $15642, tornado $1404e, car explosion $14b8e.
Reports destination-screen byte match counts over random trials."""
import sys, os, random, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
from calldiff import CallDiff
from sprites import *

dat = open(os.path.join(sscfg.FILES, 'SUPER.DAT'), 'rb').read()
b5 = bytes(dat[132566:132566 + 30000])
img = open(os.path.join(sscfg.WORK, 'ss.img'), 'rb').read()
SH = [struct.unpack_from('>2H', img, 0x157da - 0xa304 + 4 * t) for t in range(4)]
which = sys.argv[1] if len(sys.argv) > 1 else 'all'
trials = int(sys.argv[2]) if len(sys.argv) > 2 else 20
random.seed(11)
cd = CallDiff()
R = cd.ram
back = struct.unpack_from('>I', R, A4 - 78)[0]      # current draw screen (-78(A4))
other = struct.unpack_from('>I', R, A4 - 82)[0]
results = {}


def region_equal(a, b, lo, hi):
    return sum(1 for i in range(lo, hi) if a[i] == b[i]), hi - lo


if which in ('all', 'tree'):
    ok = n = 0
    for t in range(trials):
        x = random.randrange(-4, 312); y = random.randrange(20, 170); typ = random.randrange(4)
        args = struct.pack('>IhhH', other, x, y, typ)
        oc, ch, d = cd.call(0x15642, args)
        assert oc == 'returned', oc
        live = cd.apply(R[other:other + 32000], other, ch)
        mine = bytearray(R[other:other + 32000])
        rows = [struct.unpack_from('>4H', b5, 0x70e0 + typ * 128 + r * 8) for r in range(16)]
        tree_sprite(mine, x, y, rows)
        tree_shadow(mine, x, y, typ, struct.unpack_from('>16H', b5, 0x72e0 + typ * 32), SH[typ])
        a, b = region_equal(live, mine, 0, 32000)
        ok += a; n += b
        if a != b: print('  tree trial', t, 'x', x, 'y', y, 'type', typ, 'mismatch bytes', b - a)
    print('tree+shadow $15642: %d / %d screen bytes equal over %d trials' % (ok, n, trials))
if which in ('all', 'tornado'):
    ok = n = 0
    for t in range(trials):
        fr = random.randrange(3); x = random.randrange(0, 300); y = random.randrange(-6, 195)
        args = struct.pack('>Hhh', fr, x, y)
        oc, ch, d = cd.call(0x1404e, args)
        assert oc == 'returned', oc
        live = cd.apply(R[back:back + 32000], back, ch)
        mine = bytearray(R[back:back + 32000])
        rows = [struct.unpack_from('>4H', b5, fr * 128 + r * 8) for r in range(16)]
        wrench_sprite(mine, x, y, rows)
        a, b = region_equal(live, mine, 0, 32000)
        ok += a; n += b
        if a != b: print('  tornado trial', t, 'frame', fr, 'x', x, 'y', y, 'mismatch bytes', b - a)
    print('tornado $1404e: %d / %d screen bytes equal over %d trials' % (ok, n, trials))
if which in ('all', 'spin'):
    ok = n = 0
    for t in range(trials):
        car = random.randrange(4); fr = random.randrange(26)
        x = random.randrange(0, 300); y = random.randrange(31, 180)
        cd.poke_word(A4 - 3690 + 2 * car, x); cd.poke_word(A4 - 3698 + 2 * car, y)
        args = struct.pack('>HH', car, fr)
        oc, ch, d = cd.call(0x14b8e, args)
        assert oc == 'returned', oc
        live = cd.apply(R[back:back + 32000], back, ch)
        mine = bytearray(R[back:back + 32000])
        rows = [struct.unpack_from('>4H', b5, 0x5bc0 + fr * 0x70 + r * 8) for r in range(14)]
        spinout_sprite(mine, x, y, rows)
        a, b = region_equal(live, mine, 0, 32000)
        ok += a; n += b
        if a != b: print('  explosion trial', t, 'car', car, 'frame', fr, 'x', x, 'y', y, 'mismatch bytes', b - a)
    print('car explosion $14b8e: %d / %d screen bytes equal over %d trials' % (ok, n, trials))
cd.close()
