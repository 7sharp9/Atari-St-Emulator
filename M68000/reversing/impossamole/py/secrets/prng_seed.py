"""PRNG A seed source: the four counters $227ac/ae/b0/b2 advance by 1/2/3/4 per call of $beda (the gameplay VBL handler $1a2c0) and the
whole block $22798..$22806 (state $227aa included) is zero-filled by $22784 at every title/level/death transition."""
import sys
sys.path.insert(0, __file__.rsplit('/', 1)[0])
from repl import *
r = Repl('scratchpad/impossamole/agents/unpoked/s11/seg11_shaft_exit.snap')
r.cmd('s 30000')
c0 = [r.w(a) for a in (0x227ac, 0x227ae, 0x227b0, 0x227b2)]
out = r.cmd('hits 480000 beda 1a2c0 bef4')
n = {l.split()[0]: int(l.split()[1]) for l in out if l.startswith('  $')}
c1 = [r.w(a) for a in (0x227ac, 0x227ae, 0x227b0, 0x227b2)]
print('VBL handler $1a2c0 hits', n['$01a2c0'], '$beda hits', n['$00beda'], '$bef4 hits', n['$00bef4'])
print('counter deltas', [(b - a) & 0xffff for a, b in zip(c0, c1)], ' expected (1,2,3,4) x', n['$00beda'])
out = r.cmd('callcap 22784 20000')
z = [l for l in out if l.startswith('mem $0227')]
print('$22784 zero-fills:', ' '.join(l.split()[1] + l.split()[2] for l in z if l.split()[1] in ('$0227aa','$0227ab','$0227ac','$0227ad','$0227ae','$0227af','$0227b0','$0227b1','$0227b2','$0227b3')))
r.close()
