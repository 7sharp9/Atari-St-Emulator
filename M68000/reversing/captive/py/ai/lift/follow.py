"""Leg B: what a group does after the party rides away: follow.py <snap> <group index> <actions> [input ...]
Applies the inputs (drive.py syntax) first, then stops at every $10304 (cr_GroupThink) entry whose A0 is the group's
record and logs one row per action: frame (count of $102a0 calls since the inputs ended), group cell, the plane-2
byte there, bits 0-2, bits 3-5, flags +5 before -> after, the decision label reached ($10304's branch targets, as
gate_decide.py names them), the cell and facing after, and the party's cell. Env OUT=<path> saves the end state."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import probe_input as P
from probe_input import srv, w16, A6  # noqa
from fight import groups

LABELS = {0x10732: 'SPECIAL', 0x10464: 'WANDER', 0x1045e: 'FORGET', 0x103be: 'ATTACK', 0x10408: 'TURN_ATTACK',
          0x1050e: 'TURN', 0x104c6: 'FORWARD', 0x104f6: 'BEHIND_TURN'}
FACE = 'NWSE'

def predict(d, f, x, y, px, py, aware=True):
    """ai.md "Decision rule" steps 2 and 4 for a non-relentless group of a type with $10b2c = 0 (no ranged attack;
    types $e and 2 here): not aware -> WANDER; else, unless lined up with the party within 6 cells, follow the
    direction d read from its cell."""
    if not aware:
        return 'WANDER'
    if (x == px and 1 <= abs(y - py) <= 6) or (y == py and 1 <= abs(x - px) <= 6):
        return 'sight'
    if d >= 4:
        return 'FORGET'
    if f == d:
        return 'FORWARD'
    if f == d ^ 2:
        return 'FORWARD' if abs(x - px) <= 6 and abs(y - py) <= 6 else 'BEHIND_TURN'
    return 'TURN'

score = {'b3-5': 0, 'b0-2': 0}
s = srv(sys.argv[1]); gi, n = int(sys.argv[2]), int(sys.argv[3])
for inp in sys.argv[4:]:
    tot = dict.fromkeys(P.ADDRS, 0)
    P.run(s, int(inp[1:]), tot) if inp[0] == 'w' else P.drive(s, inp, tot)
    print('input', inp, 'party', w16(s, 26), w16(s, 28))
rec = groups(s)[gi][1]
print(f'group {gi} record ${rec:x}', flush=True)
frames, step0 = 0, None
print('act frame  step      cell     p2  b0-2 b3-5 +5 before  label        cell after face  +5 after  party    rule(b3-5)  control(b0-2)')
for k in range(n):
    while True:
        r = s('run', max_steps=3000000, until_pc=[0x102a0, 0x10304])
        pc = s.reg('pc')
        if pc == 0x102a0:
            frames += 1; s('step', n=1); continue
        if pc == 0x10304 and s.reg('a0') == rec:
            break
        if pc not in (0x102a0, 0x10304):
            if os.environ.get('OUT'):
                s('save', path=os.path.abspath(os.environ['OUT']))
            sys.exit(f'no arrival within budget: {r}')
        s('step', n=1)
    g = s.read(rec, 8); x, y, f5 = g[0], g[1], g[5]
    p2 = s.read(A6 + 11322 + 64 * y + x, 1)[0]
    step = int(s('regs')['step']) if 'step' in s('regs') else 0
    r = s('run', max_steps=20000, until_pc=list(LABELS) + [0x102f0])
    lab = LABELS.get(s.reg('pc'), 'none')
    s('run', max_steps=200000, until_pc=[0x102f0])
    g2 = s.read(rec, 8)
    px, py = w16(s, 26), w16(s, 28)
    m35, m02 = (predict((p2 >> 3) & 7, f5 & 3, x, y, px, py, f5 & 8), predict(p2 & 7, f5 & 3, x, y, px, py, f5 & 8))
    score['b3-5'] += m35 == lab; score['b0-2'] += m02 == lab
    print(f'{k:3d} {frames:5d} {step:9d}  ({x:2d},{y:2d})  {p2:02x}   {p2 & 7}    {(p2 >> 3) & 7}   {f5:02x} {FACE[f5 & 3]}    '
          f'{lab:12s} ({g2[0]:2d},{g2[1]:2d})  {FACE[g2[5] & 3]}    {g2[5]:02x}      ({px},{py})  {m35:11s} {m02}', flush=True)
    print('model matches', score, 'of', k + 1, flush=True) if k == n - 1 else None
if os.environ.get('OUT'):
    s('save', path=os.path.abspath(os.environ['OUT']))
s.close()
