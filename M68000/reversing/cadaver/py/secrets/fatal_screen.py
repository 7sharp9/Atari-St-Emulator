"""fatal_screen.py: the engine's assert handler $011788 clears the top of the screen, prints the caller's message (A0) at line 0, then
"CONTACT STEVE OR MIKE AT HQ" ($0117d0) at line 10 via the text routine $011466 and spins in `bra $117c4` forever.  There are 67
call sites (assert_sites.py).  Start gameplay_empire.snap: patch `jsr $011788.l / nop` over the instruction at the current PC (one
REPL `w` pair), run 400,000 steps, then confirm the main loop ($006ba2) is gone (0 hits) and the spin loop ($0117c4) is where the
time goes, and save the screen.
    uv run python reversing/cadaver/py/secrets/fatal_screen.py <out.snap>      (render with tools/snap_render.py)"""
import sys
sys.path.insert(0, __file__.rsplit('/', 1)[0])
from repl import *
r = Repl()
pc = r.pc()
r.cmd(f'w {pc:x} 4eb90001', f'w {pc + 4:x} 17884e71', 's 400000')
h = r.hits(200000, 0x6ba2, 0x117c4)
print('main loop hits', h[0x6ba2], ' spin-loop hits', h[0x117c4])
if len(sys.argv) > 1: r.snap(sys.argv[1])
r.close()
