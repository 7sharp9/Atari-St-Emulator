"""classes_live.py: prove the per-frame creature-class behaviour dispatch ($00e25c-$00e28c -> $00e298 -> overlay header record
k = 9+class, first word).  Start snapshot scratchpad/cadaver/gameplay_empire.snap (level 0 overlay).  A live creature list
(396(A5): count word + type-6 object ids) is primed with the GIANT RAT record (type 6 id 194 at $070034, instance at +30, class
byte at instance+1 = $070053) and its class byte is set to k = 1..10; 120,000 steps are run with `hits` on the class routine
entry ($04c65e + record word + 2) and on the dispatch instruction $00e28c (bsr $e298).
Expected: for each class the routine is hit >= 1 times (once per frame) and $00e28c is hit the same number of times."""
import sys, struct
sys.path.insert(0, 'reversing/cadaver/py/secrets/overlay')
from ov import *
BASE = 0x4c65e
ov = open('scratchpad/cadaver/secrets_out/overlay/overlay_level0.bin', 'rb').read()[4:]
W = lambda o: struct.unpack_from('>H', ov, o)[0]
ok = 0
for k in range(0, 11):
    rec = 4 * (9 + k)
    tgt = BASE + W(rec) + 2 if k else None
    r = Repl()
    wb(r, a5(396) + 1, 1)                      # count word (high byte is already 0): low byte at +1
    ww(r, a5(398), 194)
    wb(r, 0x70053, k)
    addrs = [0xe28c] + ([tgt] if tgt else [])
    h = r.hits(120000, *addrs)
    if k:
        print('class %2d routine $%06x record word $%04x: hits %d   dispatch $e28c: %d' % (k, tgt, W(rec), h[tgt], h[0xe28c]))
        ok += h[tgt] >= 1 and h[tgt] == h[0xe28c]
    else:
        print('class  0 (no behaviour): dispatch $e28c hits', h[0xe28c])
    r.close()
print('classes matched', ok, 'of 10')
