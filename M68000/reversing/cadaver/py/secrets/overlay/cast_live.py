"""cast_live.py: drive a REAL spell cast (fire button with a spell scroll selected) and watch the dispatch at $00f0e4.
Start snapshot scratchpad/cadaver/gameplay_empire.snap.  The PARCHMENT object (type 6 id 471, instance at $0719de) is turned
into a scroll by poking its instance: byte0 = spell id, +4 word = target object id, +7 = 1 (learned/castable); then
1262(A5) = 471 (selected object), 2463(A5) = 1 (spell-cast action mode), 2306(A5) = 0, and joystick-1 fire ($80) is held.
Usage: cast_live.py <spell id> <target object id>.  Prints hits on $00f02e ($006faa jsr), $00f0e4 (jsr (A0) into the overlay), the overlay entry, and registers at $00f0e4."""
import sys, struct
sys.path.insert(0, 'reversing/cadaver/py/secrets/overlay')
from ov import *
BASE = 0x4c65e
ov = open('scratchpad/cadaver/secrets_out/overlay/overlay_level0.bin', 'rb').read()[4:]
W = lambda o: struct.unpack_from('>H', ov, o)[0]; S = lambda o: struct.unpack_from('>h', ov, o)[0]
spell = int(sys.argv[1]) if len(sys.argv) > 1 else 4
tgt_id = int(sys.argv[2]) if len(sys.argv) > 2 else 257
t2 = W(4)
entry = BASE + t2 + S(t2 + 2 * spell)
r = Repl()
inst = 0x719de
wb(r, inst, spell); wb(r, inst + 1, 10); ww(r, inst + 4, tgt_id); wb(r, inst + 7, 1)
ww(r, a5(1262), 471); wb(r, a5(2463), 1); wb(r, a5(2306), 0)
print('inst', r.mem(inst, 12).hex(), '1262', r.mem(a5(1262), 2).hex(), '2463', r.mem(a5(2463), 1).hex())
r.cmd('kbd ff', 's 300', 'kbd 80')
h = r.hits(200000, 0x6faa, 0xf02e, 0xf0e4, entry)
print('hold fire 200k steps: $6faa=%d $f02e=%d $f0e4=%d overlay $%06x=%d' % (h[0x6faa], h[0xf02e], h[0xf0e4], entry, h[entry]))
r.cmd('kbd 00')
print('after: 2466=%s 2307(timers)=%s list=%s flags 2342/2345/2346/2467=%s %s %s %s' % (r.mem(a5(2466), 1).hex(), r.mem(a5(2307), 1).hex(), r.mem(a5(2412), 2).hex(), r.mem(a5(2342), 1).hex(), r.mem(a5(2345), 1).hex(), r.mem(a5(2346), 1).hex(), r.mem(a5(2467), 1).hex()))
r.close()
