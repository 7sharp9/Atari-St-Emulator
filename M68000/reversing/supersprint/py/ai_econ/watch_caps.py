"""watch_caps.py <fire|idle> [steps]  - prove the speed-cap array -3874(A4) is written only at race start.

Resumes data/prerace_k.snap (paused at $c156 = the first cap write of the race-start initialiser in $be40, human in
slot 1, drones in slots 0,2,3; make with prerace.py), sets `watch` on the four cap words, then runs `steps` (default 25M
= the whole race + WINNER'S CIRCLE) either with the human holding fire (accelerate; `fire`) or never touching the pad
(`idle`).  Prints every write (step, pc, addr, value) and a per-PC summary.

    cd M68000 && python3 reversing/supersprint/py/ai_econ/watch_caps.py fire
"""
import collections
from aiutil import *

mode = sys.argv[1] if len(sys.argv) > 1 else 'fire'
steps = int(sys.argv[2]) if len(sys.argv) > 2 else 25_000_000
r = Repl2(os.path.join(DATA, 'prerace_k.snap'))
r.cmd('watch %x 8' % (A4 - 3874))
if mode == 'fire':
    r.cmd('kbd fe 80')
writes = []
done = 0
while done < steps:
    n = min(1_000_000, steps - done)
    out, _ = r.cmd('s %d' % n)
    done += n
    writes += [l for l in out if l.startswith('WATCH')]
st = {}
for l in writes:
    m = re.match(r'WATCH: step=(\d+) pc=\$([0-9a-f]+) WriteWord \$([0-9a-f]+) <- \$([0-9a-f]+)', l)
    st.setdefault((m.group(2)), []).append((int(m.group(1)), m.group(3), m.group(4)))
print('mode', mode, 'steps', steps, 'total watch lines', len(writes))
for pc, v in sorted(st.items()):
    print(' pc $%s: %d writes, steps %d..%d' % (pc, len(v), v[0][0], v[-1][0]))
first = int(re.match(r'WATCH: step=(\d+)', writes[0]).group(1)) if writes else None
late = [l for l in writes if int(re.match(r'WATCH: step=(\d+)', l).group(1)) > first + 2000]
print('writes more than 2000 steps after the init burst:', len(late))
print('final caps', r.a4w(-3874), 'speeds', r.a4w(-3730), 'laps', r.a4w(-3906))
r.close()
