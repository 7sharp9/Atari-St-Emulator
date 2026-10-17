"""prize_calls.py - list the calls of the score adder $16084(car, desc) in the winner's circle when the human (slot 1) finishes rank 0:
(car, descriptor digits) per call, and the running score.  Shows what is added (prize 1000/500/250 and the other terms)."""
from lt import *
def val(d):
    s = 0
    for x in d: s = s * 10 + (x & 0x7f)
    return s
r = Repl2(os.path.join(AI, 'pre_winner.snap'))
pk = {}
ranking = [1, 0, 2, 3]
for pos, c in enumerate(ranking):
    pk[A4 - 3906 + 2 * c] = 4 - pos; pk[A4 - 3850 + 2 * c] = 5; pk[A4 - 3842 + 2 * c] = 0
for c in range(3): pk[A4 - 3954 + 2 * c] = 0
pk[A4 - 3914 + 2] = 0
setwords(r, pk)
calls = []
used = 0
while used < 40_000_000:
    out, regs = r.cmd('bp 16084 400000')
    if not any('hit' in l for l in out): break
    used += int(re.search(r'after (\d+) step', ' '.join(out)).group(1))
    sp = regs['A7']
    car = r.words(sp + 4, 1)[0]; dp = struct.unpack('>I', r.mem(sp + 6, 4))[0]
    ret = struct.unpack('>I', r.mem(sp, 4))[0]
    if dp > 0xf0000 or car not in (0, 1, 2, 3):
        calls.append((ret, car, -1, -1)); continue
    calls.append((ret, car, val(list(r.mem(dp, 6))), val(list(r.mem(A4 - 4846 + 6 * car, 6)))))
    if len(calls) > 400: break
import collections
c = collections.Counter((x[0], x[1], x[2]) for x in calls)
print('calls', len(calls))
for k, v in sorted(c.items()): print('  ret $%x car %d descriptor %d x %d' % (k[0], k[1], k[2], v))
print('score slot 1 at the end', val(list(r.mem(A4 - 4840, 6))))
r.close()
