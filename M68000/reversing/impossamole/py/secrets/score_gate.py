"""High-score gate: $19f5a compares the score $19c1a with the five table scores (cmp.l; ble = table <= score) and returns carry set only if the score ties or beats
one; $182d8 (bcc $183b4) skips the name entry otherwise.  Death path with the score poked to 1999, 2000 and 999999 (score is a plain longword at $bb6e)."""
import sys
sys.path.insert(0, __file__.rsplit('/', 1)[0])
from repl import *
for score in (1999, 2000, 999998, 999999):
    r = Repl('scratchpad/impossamole/agents/unpoked/s11/seg11_shaft_exit.snap')
    r.cmd('w bb6e %08x' % score)
    r.cmd('w bb74 00120300')
    go = r.until(0x17fe8, 20000000)
    e = r.until(0x182bc, 20000000)
    y = r.until(0x19dfc, 3000000)
    n = r.until(0x183b4, 3000000)
    print(f'score {score:6d}: game over {go}, $182bc {e}, name entry loop $19dfc reached {y}, straight to $183b4 (no entry) {n and not y}, rank cell $19c20 = {r.b(0x19c20)}')
    r.close()
