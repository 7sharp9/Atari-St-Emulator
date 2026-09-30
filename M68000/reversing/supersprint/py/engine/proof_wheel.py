"""Differential test of $16926 (vertical flip) and $16962 (horizontal mirror) that build the 16 steering-wheel frames."""
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
from calldiff import CallDiff
from wheel import *

dat = open(os.path.join(sscfg.FILES, 'SUPER.DAT'), 'rb').read()
b2 = dat[12608:12608 + 7190]
cd = CallDiff(); R = cd.ram
BUF = 0x72000
cd.poke(BUF, b2[0x96:0x96 + 7040] + bytes(22528 - 7040))
want = all_frames(b2)
ok = tot = 0
for j in range(5, 16):
    if j < 9: fn, src = 0x16926, 8 - j
    else: fn, src = 0x16962, 16 - j
    if j >= 9:                      # callcap restores RAM after each call: feed the source frames 5..8 built by the vertical flips
        for k in range(5, 9): cd.poke(BUF + k * 1408, want[k])
    oc, ch, d = cd.call(fn, struct.pack('>IHH', BUF, src, j))
    assert oc == 'returned', oc
    live = cd.apply(cd.ram[BUF:BUF + 22528], BUF, ch)
    # the routine writes only frame j; compare that frame
    got = live[j * 1408:(j + 1) * 1408]
    eq = sum(1 for a, b in zip(got, want[j]) if a == b)
    ok += eq; tot += 1408
    print('frame %2d from %2d via $%x: %d / 1408 bytes equal' % (j, src, fn, eq))
print('WHEEL TOTAL %d / %d' % (ok, tot))
cd.close()
