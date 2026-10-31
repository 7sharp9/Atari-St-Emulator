"""push_probe.py <snap> <dirs> <chunks> [strength]: hold `dirs` (U D L R, one or two) and print, per 20,000-step chunk, the hero's bbox, the post 380's
placement rect, the hits on the push path and the strength 2144(A5) / push budget 1234(A5) words.  With `strength`, 2144(A5) alone is set first (a control:
the next word, 2146(A5), the touch cache count, is written back unchanged).  SITES (env, hex words) replaces the default sites:
  $7368 blocked walk -> $931a, $938c non-solid result, $ed5a push routine, $eeca weight charge, $eeac solid in the way, $ef84 refusal, $ef94 apply, $9440 touch list.
mechanics.md section 3, "Pushing".  The A/B there: north.snap from the 96th-pass record scratchpad/cadaver/s96/r6/s3_flask.snap (post at (16..24, 32..40),
strength 50) by `explore.py s3_flask.snap north.snap S200000 GR:x>=33 GU:y<=30 GL:x<=24 =x23` (hero (17..23, 24..30)), then
`push_probe.py north.snap D 8` (refused at $ef84, budget -90) and `push_probe.py north.snap D 8 199` (applied at $ef94, the post to y 34..42)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
ARGS = [os.path.abspath(sys.argv[1])] + sys.argv[2:]            # before the import: lib/drv.py chdirs on import
from explore import *
inp, dirs, n = ARGS[0], ARGS[1], int(ARGS[2]); strength = int(ARGS[3]) if len(ARGS) > 3 else None
SITES = [int(a, 16) for a in os.environ.get('SITES', '7368 938c ed5a ee88 eeac eeca ef40 ef84 ef94 9440').split()]
r = Repl(inp)
if strength is not None:
    lw = r.mem(A5 + 2144, 4); r.cmd('w %x %04x%s' % (A5 + 2144, strength, lw[2:].hex()))
r.cmd('s 200000')                                                   # the first hold after a reload starts about 120,000 steps late
b = 0
for ch in dirs: b |= K[ch]
joy(r, b)
for i in range(n):
    h = r.hits(20000, *SITES)
    print(i, pos(r), orect(r, 380), ' '.join('%x:%d' % (a, h.get(a, 0)) for a in SITES if h.get(a, 0)), 'strength', r.w(A5 + 2144), 'budget', (r.w(A5 + 1234) ^ 0x8000) - 0x8000)
joy(r, 0); r.close()
