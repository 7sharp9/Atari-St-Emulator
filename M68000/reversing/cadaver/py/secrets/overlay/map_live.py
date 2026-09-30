"""map_live.py: prove spell id 4 (MAP) live.  Start snapshot: scratchpad/cadaver/gameplay_empire.snap.
1. baseline: F1 (scancode $3b) held -> hits on $00a9a8 and 2466(A5) value while the map is up; snapshot to out/map_f1.snap.
2. MAP path: callcap-free poke of (A5)+2466 = $81 (exactly what overlay spell[4] $04ce4c does), run, count hits on $00a9a8 and read
   2466(A5) afterwards (main loop $006b92 clears bit 7, leaves 1); snapshot to out/map_spell.snap.
Expected: $a9a8 hits 1 in each run; 2466 stays 0 in run 1, becomes $01 in run 2 (bit 7 consumed)."""
import sys
sys.path.insert(0, 'reversing/cadaver/py/secrets/overlay')
from ov import *
out = 'scratchpad/cadaver/secrets_out/overlay/out/'
r = Repl()
print('base PC', hex(r.pc()), '2466..', r.mem(a5(2466), 4).hex())
h = r.hits(400000, 0xa9a8)
print('idle 400k steps: hits', h)
r.close()
# run 1: F1
r = Repl()
r.cmd('kbd 3b'); r.cmd('s 40000'); r.cmd('kbd bb')
h = r.hits(2000000, 0xa9a8, 0xab34)
print('F1 run: hits', h, '2466 =', r.mem(a5(2466), 1).hex())
r.snap(out + 'map_f1.snap')
r.close()
# run 2: MAP
r = Repl()
wb(r, a5(2466), 0x81)
print('poked 2466 ->', r.mem(a5(2466), 4).hex())
h = r.hits(2000000, 0xa9a8, 0xab34)
print('MAP run: hits', h, '2466 =', r.mem(a5(2466), 1).hex())
r.snap(out + 'map_spell.snap')
r.close()
