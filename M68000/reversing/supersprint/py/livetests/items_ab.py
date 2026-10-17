"""items_ab.py <arm> [frames] - does shop item 3 ("increase score level taken") have any gameplay consumer?

Same snapshot (ai_econ/prerace_b.snap, paused at $bec0 = top of $be40's per-car init loop, human in slot 1), same budget, fire held, one variable:
the human's upgrade level for item k set to 5 (word -4066+2k (A4), slot 1; levels are -4074+8*car+2*item):
  ctl  nothing poked         i0 traction   i1 top speed   i2 turbo   i3 "increase score level"
Samples once per frame at the entry of $df18 (frame-aligned) the whole A4 window [A4-9000, A4+300) (every game global) and writes
data/items_<arm>.npy-like json (list of hex strings).  items_cmp.py compares each arm with ctl.
"""
from lt import *
import hashlib
arm = sys.argv[1]
frames = int(sys.argv[2]) if len(sys.argv) > 2 else 500
r = Repl2(os.path.join(AI, 'prerace_b.snap'))
if arm != 'ctl':
    k = int(arm[1])
    setwords(r, {A4 - 4066 + 2 * k: 5})
r.cmd('kbd fe 80')
W0, WN = A4 - 9000, 9300
snaps = []
out, _ = r.cmd('bp df18 12000000'); assert any('hit' in l for l in out), out[-3:]
for f in range(frames):
    snaps.append(r.mem(W0, WN).hex())
    out, _ = r.cmd('bp df18 400000'); assert any('hit' in l for l in out), out[-3:]
json.dump({'arm': arm, 'W0': W0, 'snaps': snaps}, open(os.path.join(DATA, 'items_%s.json' % arm), 'w'))
print(arm, 'frames', len(snaps), 'levels slot 1', r.a4w(-4066, 4), 'caps', r.a4w(-3874, 4), 'div', r.a4w(-3882, 4))
r.close()
