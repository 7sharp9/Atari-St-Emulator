"""demo_caps.py - the second cap/divisor writer: the attract-demo race initialiser $caa8 (thunk 60(A5), called at $13954).
From ss_attract.snap run to $caa8, read its argument T, then watch -3882..-3867 and report writes (pc, value) + final caps."""
from lt import *
r = Repl2(os.path.join(sscfg.WORK, 'ss_attract.snap'))
out, regs = r.cmd('bp caa8 60000000')
print('hit caa8:', any('hit' in l for l in out), 'step lines', [l for l in out if 'hit' in l or 'step' in l][:2])
A6 = regs['A7']                      # on entry (before link) the stack holds ret addr then the arg word
T = r.words(regs['A7'] + 4, 1)[0]
print('entry A7=%x track arg T=%d R=%s' % (regs['A7'], T, r.a4w(-1748, 1)))
r.cmd('watch %x 16' % (A4 - 3882))
lines = []
for i in range(30):
    out, _ = r.cmd('s 100000')
    lines += [l for l in out if l.startswith('WATCH')]
pcs = {}
for l in lines:
    m = re.match(r'WATCH: step=(\d+) pc=\$([0-9a-f]+) WriteWord \$([0-9a-f]+) <- \$([0-9a-f]+)', l)
    pcs.setdefault(m.group(2), []).append((int(m.group(1)), (int(m.group(3), 16) - (A4 - 3882)), m.group(4)))
for pc, v in pcs.items():
    print(' pc $%s: %d writes, first step %d, last %d; (offset-in-16B, value) %s' % (pc, len(v), v[0][0], v[-1][0], [(o, int(x, 16)) for _, o, x in v][:12]))
print('caps', r.a4w(-3874, 4), 'div', r.a4w(-3882, 4), 'drone', r.a4w(-3914, 4), 'predicted 110-4T+4slot =', [110 - 4 * T + 4 * i for i in range(4)])
r.close()
