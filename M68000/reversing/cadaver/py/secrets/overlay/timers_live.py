"""timers_live.py: prove the overlay's table 3 (timer-expiry handlers, header word +6) is what $00904e dispatches.
Start snapshot scratchpad/cadaver/gameplay_empire.snap (level 0 overlay at $04c65e).  For each timer id in the table:
poke one active timer (prescaler 2460(A5)=1 so the next frame ticks, 2307(A5)=1, 2412(A5)[0]=id, 2308(A5)+id=1 i.e. expires on the next tick), run 100,000 steps
with `hits` on the handler entry and on $00904e (the dispatch site), and report the hit counts and the A5 fields the handler
touches before/after.  Expected: dispatch site $00904e hit once per timer (count 1), handler hit once, 2307 back to 0,
list slot back to $ff."""
import sys
sys.path.insert(0, 'reversing/cadaver/py/secrets/overlay')
from ov import *
BASE = 0x4c65e
import struct
ov = open('scratchpad/cadaver/secrets_out/overlay/overlay_level0.bin', 'rb').read()[4:]
W = lambda o: struct.unpack_from('>H', ov, o)[0]; S = lambda o: struct.unpack_from('>h', ov, o)[0]
t3 = W(6)
ids = [0, 1, 2, 3, 4, 5, 6, 7, 32, 33, 34, 35, 36, 37, 38, 39, 40]
watch = [2434, 2436, 2437, 2279, 2280, 2299, 2467, 2144, 316]
def snapf(r): return {o: r.mem(a5(o), 4).hex() for o in watch}
ok = 0
for tid in ids:
    tgt = BASE + t3 + S(t3 + 2 * tid)
    r = Repl()
    # prime some state so the handlers have something to undo
    wb(r, a5(2434), 5); wb(r, a5(2436), 0x7f); wb(r, a5(2467), 1)
    wb(r, a5(2279), 2); wb(r, a5(2280), 2)
    wb(r, a5(2460), 1); wb(r, a5(2307), 1); wb(r, a5(2412), tid); wb(r, a5(2308 + tid), 1)
    before = snapf(r)
    h = r.hits(100000, tgt, 0x904e)
    after = snapf(r)
    cnt = r.mem(a5(2307), 1).hex(); slot = r.mem(a5(2412), 1).hex()
    diff = {o: (before[o][:2], after[o][:2]) for o in watch if before[o][:2] != after[o][:2]}
    print('timer %2d handler $%06x hits=%d dispatch$904e=%d  2307=%s slot0=%s  changed(A5+off: before->after)=%s' % (tid, tgt, h[tgt], h[0x904e], cnt, slot, diff))
    if h[tgt] == 1 and h[0x904e] == 1: ok += 1
    r.close()
print('matched', ok, 'of', len(ids))
