"""SPACE key in every world: $227ff takes the world index ($ee06), the per-world routine from $ee16 runs, and $227ff ends at $ff.  Snapshots: each world's gameplay snapshot."""
import sys
sys.path.insert(0, __file__.rsplit('/', 1)[0])
from repl import *
from hidden_keys import key
A = 'scratchpad/impossamole/agents/'
S = [(1, A+'world12/klondike_gameplay.snap'), (2, A+'world12/orient_gameplay.snap'), (3, A+'unpoked/s11/seg11_shaft_exit.snap'),
     (4, A+'world34/snaps/ice_gameplay.snap'), (5, A+'world34/snaps/bermuda_gameplay.snap')]
for w, snap in S:
    r = Repl(snap); r.cmd('s 30000')
    bb = r.b(0xbb76)
    before = sum(1 for i in range(5) if r.w(0x1a5de + 108*i))
    key(r, 0x39, hold=60000)
    seen = r.b(0x227ff)
    r.cmd('s 4000000')
    after = sum(1 for i in range(5) if r.w(0x1a5de + 108*i))
    print(f'world {w} ($bb76={bb}): $227ff right after the key {seen}, 4M steps later {r.b(0x227ff):#x}; live enemy slots {before} -> {after}; hp {r.b(0xbb74)}')
    r.close()
