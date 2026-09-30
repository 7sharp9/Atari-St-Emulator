"""At every note-on: after the base period is stored ($1dd4e) 74(A0) must equal the word at $1f6d6 + 2*(note + transpose)  (the YM tone-period table)."""
import sys
sys.path.insert(0, __file__.rsplit('/', 1)[0])
from repl import *
from prng import parse_regs
r = Repl('scratchpad/impossamole/agents/secrets/data/title_bb7b_0.snap')
tab = [int.from_bytes(r.mem(0x1f6d6 + 2*i, 2), 'big') for i in range(96)]
ok = n = 0
for i in range(150):
    o = r.cmd('bp 1dd22 3000000')
    rg = parse_regs(o); a0 = rg['A0']; d0 = rg['D0'] & 0xffff
    trans = int.from_bytes(r.mem(a0 + 64, 2), 'big', signed=True)
    r.cmd('bp 1dd4e 200')
    per = r.w(a0 + 74)
    good = per == tab[(d0 + trans)] if 0 <= d0 + trans < 96 else False
    n += 1; ok += good
    if not good: print('  mismatch: note', d0, 'trans', trans, 'period 74(A0) =', per, 'glide state 42(A0) =', hex(r.w(a0 + 42)), 'table', tab[(d0 + trans) % 96] if 0 <= d0 + trans < 96 else None)
    r.cmd('s 1')
print(f'{ok} / {n} note-ons: 74(A0) == period table[note+transpose]')
r.close()
