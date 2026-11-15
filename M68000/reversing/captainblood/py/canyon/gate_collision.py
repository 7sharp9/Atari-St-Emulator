"""Gate: the collision predicate of the canyon flight, model vs the emulator at the instruction.
At $10c24 (cmp.w 26(A6),D0) the game holds D0 = ((T[o]+T[o+1])>>1)+1 (T = bytes at $70400, o = the path word at
$10a8a + (A6)) and compares it with the altitude word $10a66; D0 > altitude (bls fails) goes to the bump ($10c2c), else
to $10c7c. Model: D0 == register D0, and the next PC == the model's branch.
Labelled pokes (the natural flight is above every row, so it never bumps): at each stop the altitude word is poked to
D0 (equality, must not bump) in one process for N rows, and to D0-1 (must bump) in NB separate resumes.
Broken controls: no +1, a shifted column, a >= compare. Run from M68000/:
  uv run python reversing/captainblood/py/canyon/gate_collision.py [N] [NB]"""
import sys, os, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from repl import Repl
N = int(sys.argv[1]) if len(sys.argv) > 1 else 40
NB = int(sys.argv[2]) if len(sys.argv) > 2 else 12
snap = 'scratchpad/captainblood/canyon/main_loop.snap'

def stop(r, delta):
    out = r.cmd('bp 10c24 3000000')
    m = re.search(r'D0:([0-9a-f]{8})', out); pc = re.search(r'PC: ([0-9a-f]+)', out)
    if not m or int(pc.group(1), 16) & 0xffffff != 0x10c24:
        return None
    d0 = int(m.group(1), 16) & 0xffff
    idx = r.w(0x10a4c, 2); o = r.w(0x10a8a + (idx & 0xfc), 2); T = r.mem(0x70400 + o, 3)
    r.cmd(f'ww 10a66 {(d0 + delta) & 0xffff:04x}')
    alt = r.w(0x10a66, 2)
    out2 = r.cmd('s 2', 'r')
    return (d0, T, alt, int(re.search(r'PC: ([0-9a-f]+)', out2).group(1), 16))

rows = []
r = Repl(snap)
for n in range(N):
    x = stop(r, 0)
    if x: rows.append(x)
    r.cmd('s 20000')
r.close()
for n in range(NB):
    r = Repl(snap); r.step(23000 * n + 1000)
    x = stop(r, -1)
    if x: rows.append(x)
    r.close()

def model(T, bug):
    if bug == 'nop1': return (T[0] + T[1]) >> 1
    if bug == 'col': return ((T[1] + T[2]) >> 1) + 1
    return ((T[0] + T[1]) >> 1) + 1
def branch(d0, alt, bug):
    return 0x10c2c if (d0 >= alt if bug == 'ge' else d0 > alt) else 0x10c7c
for bug in ('none', 'nop1', 'col', 'ge'):
    okD = sum(model(T, bug) == d0 for d0, T, a, pc2 in rows)
    okB = sum(branch(model(T, bug), a, bug) == pc2 for d0, T, a, pc2 in rows)
    print(f'model {bug:5s}: D0 match {okD}/{len(rows)}, branch match {okB}/{len(rows)}')
print('bump', sum(pc2 == 0x10c2c for *_, pc2 in rows), 'no-bump', sum(pc2 == 0x10c7c for *_, pc2 in rows),
      'other', sum(pc2 not in (0x10c2c, 0x10c7c) for *_, pc2 in rows))
