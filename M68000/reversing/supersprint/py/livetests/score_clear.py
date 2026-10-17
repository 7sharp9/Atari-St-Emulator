"""score_clear.py - who clears a human's 6-digit score when it finishes below rank 0 (prize_score.py: 310 -> 0)?  bp on $15ffe (the digit
clear/store routine written at $16028) from pre_winner.snap with the human at rank 1; print caller (return address), car arg, score at each hit."""
from lt import *
def val(d):
    s = 0
    for x in d: s = s * 10 + (x & 0x7f)
    return s
r = Repl2(os.path.join(AI, 'pre_winner.snap'))
pk = {}
ranking = [0, 1, 2, 3]
for pos, c in enumerate(ranking):
    pk[A4 - 3906 + 2 * c] = 4 - pos; pk[A4 - 3850 + 2 * c] = 5; pk[A4 - 3842 + 2 * c] = 0
for c in range(3): pk[A4 - 3954 + 2 * c] = 0
pk[A4 - 3914 + 2] = 0
setwords(r, pk)
seen = []
used = 0
for i in range(40):
    out, regs = r.cmd('bp 15ffe 40000000')
    if not any('hit' in l for l in out): break
    sp = regs['A7']
    ret = struct.unpack('>I', r.mem(sp, 4))[0]; arg = r.words(sp + 4, 1)[0]
    seen.append((hex(ret), arg, val(list(r.mem(A4 - 4840, 6)))))
    if ret == 0 or ret > 0x100000: break
print('calls of $15ffe (ret, arg word, slot-1 score at entry):', seen[:12], 'total', len(seen))
print('end score', val(list(r.mem(A4 - 4840, 6))), 'drone flags', r.a4w(-3914, 4))
r.close()
