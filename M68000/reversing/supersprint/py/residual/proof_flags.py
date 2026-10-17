"""-150/-148 flags: $101bc (the patched protection check) and the save routine $1000e's guard, by callcap.
$101bc: -150 := 0, -148 := 1, D5 := 8 (the patch's own constant; nothing reads D5 afterwards).  $1000e with -148 == 0: -150 := 1 and returns without writing.
$1000e with -150 != 0, -148 == 1: returns without a file call (no memory change).  usage: proof_flags.py"""
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rcommon import *
os.environ['ENGINE_OUT'] = os.path.join(AGENT, 'engine_out')
from common import *
from calldiff import CallDiff
cd = CallDiff(); P = 'A5=a304 A4=1eb44'
def flags(): return struct.unpack_from('>HH', cd.ram, A4 - 150)
def after(ch): return tuple(ch.get(A4 - 150 + i, cd.ram[A4 - 150 + i]) for i in range(4))
ok = 0
for before in ((5, 0), (1, 7), (0, 1)):
    cd.poke(A4 - 150, struct.pack('>HH', *before))
    oc, ch, d = cd.call(0x101BC, presets=P); a = after(ch)
    print('$101bc  before (-150,-148)=%s -> %s, D5 = %d, outcome %s' % (before, (a[0] << 8 | a[1], a[2] << 8 | a[3]), d['regN'][5], oc)); ok += (a == (0, 0, 0, 1) and d['regN'][5] == 8)
for before, want in (((0, 0), (1, 0)), ((1, 1), (1, 1))):
    cd.poke(A4 - 150, struct.pack('>HH', *before))
    oc, ch, d = cd.call(0x1000E, presets=P); a = after(ch); got = (a[0] << 8 | a[1], a[2] << 8 | a[3])
    print('$1000e  before (-150,-148)=%s -> %s (expected %s), outcome %s, steps %d, other memory changes %d' % (before, got, want, oc, d['steps'], len([k for k in ch if not (A4 - 150 <= k < A4 - 146)])))
    ok += (got == want)
print('flag behaviours as read: %d / 5' % ok)
cd.close()
