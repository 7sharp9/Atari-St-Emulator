"""flags_live.py: prove that a spell's timer countdown byte doubles as the engine's 'effect active' flag.  Start snapshot
scratchpad/cadaver/gameplay_empire.snap with the class-2 creature primed as in classes_live.py (GIANT RAT record, class byte $070053
= 2, creature list 396(A5) = [1][194]); 240,000 steps with `hits` on the class-2 behaviour ($04c75e) for:
 baseline; FREEZE (2342(A5) = timer 34's countdown, != 0: $00e1fa skips the whole event/creature pass); SLOW CREATURE (2467(A5) = 1:
 $00e1fa runs the pass every other frame).  Expected: baseline N hits, FREEZE 0, SLOW about N/2."""
import sys
sys.path.insert(0, 'reversing/cadaver/py/secrets/overlay')
from ov import *
def run(label, pokes):
    r = Repl()
    wb(r, a5(396) + 1, 1); ww(r, a5(398), 194); wb(r, 0x70053, 2)
    for off, v in pokes: wb(r, a5(off), v)
    h = r.hits(240000, 0x4c75e, 0xe28c, 0xe1fa)
    print('%-28s class-2 routine hits %2d  (dispatch $e28c %2d, pass entry $e1fa %2d)' % (label, h[0x4c75e], h[0xe28c], h[0xe1fa]))
    r.close()
run('baseline', [])
run('FREEZE (2342(A5) = 5)', [(2342, 5)])
run('SLOW CREATURE (2467(A5) = 1)', [(2467, 1)])
