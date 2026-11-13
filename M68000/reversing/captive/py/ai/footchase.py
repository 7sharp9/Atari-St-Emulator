"""A natural chase scored per action against the party's footprints (ai.md "The trail").

footchase.py <snap> <group> <max_steps> <plan> [out.snap]

Runs the snapshot with no pokes; the only input is keypad presses from <plan>. Every entry of $10304 (cr_GroupThink)
with A0 = the record of group <group> (list index, walked afresh at each stop, so a compaction cannot mislabel it)
is one action: the script records the state on entry (group cell, facing, +5 flags, lead type, the frame RNG
15530(A6), the party's position, the plane-2 byte at the group's cell), runs to the return address on the stack,
and records the cell and facing after. The decision branch is labelled from the entry state with gate_decide.model
(reversing/captive/py/ai): sight (lined up 1-6 cells), trail (otherwise, aware), wander, forget, special. Each
action's observed move (step N/W/S/E, turn to N/W/S/E, none) is scored for a trail action against bits 3-5 of the
cell's byte (the footprint) and, as the control, against bits 0-2 (the generator's dig arrow) with fits().

<plan>: ';'-separated items 'N:k,k,...' = after group action N has returned (N = 0: at the start), press these
keypad keys one at a time as keys.py does (make, 60,000 steps, break, 300,000 steps).
Keys ($68 forward, $67/$69 turn, $6a/$6c strafe) are hex. Prints one line per key (party cell, facing) and per
action, then the score. Saves the end state to [out.snap] if given."""
import os, sys, struct
HERE = os.path.dirname(os.path.abspath(__file__))
def _root():
    d = os.environ.get('M68000_ROOT') or HERE
    while not os.path.exists(os.path.join(d, 'tools', 'rdis.py')):
        nd = os.path.dirname(d)
        if nd == d: sys.exit('repo root (tools/rdis.py) not found')
        d = nd
    return d
sys.path.insert(0, os.path.join(_root(), 'reversing', 'captive', 'py', 'ai'))
from cap import A6, srv, w16  # noqa: E402
from gate_decide import model  # noqa: E402

THINK = 0x10304
DIRS = 'NWSE'
DXY = {0: (0, -1), 1: (-1, 0), 2: (0, 1), 3: (1, 0)}

def group_addr(s, gi):
    blob = s.read(A6 + 4532, 0x1000); a = 0; i = 0
    while True:
        sz = struct.unpack('>h', blob[a + 2:a + 4])[0]
        if sz < 0: return None
        if i == gi: return A6 + 4532 + a
        a += sz; i += 1

def branch(cx, cy, f5, typ, px, py, p2):
    if f5 & 0x20: return 'special'
    if not f5 & 8 or typ in (6, 8): return 'wander'
    dx, dy = abs(cx - px), abs(cy - py)
    if (dx == 0 and 1 <= dy <= 6) or (dy == 0 and 1 <= dx <= 6): return 'sight'
    if dx == 0 and dy == 0: return 'wander'
    if f5 & 0x40: return 'wander'
    return 'forget' if (p2 >> 3) & 7 > 3 else 'trail'

def fits(move, d, face):
    """Does the observed move follow direction d from facing `face`? A step must go d. A turn from 90 degrees off
    must end facing d; a turn from facing away (d behind) must end a quarter off d (left or right at random)."""
    kind, to = move
    if kind == 'step': return to == d
    if kind == 'turn':
        rel = (face - d) & 3
        return to == d if rel in (1, 3) else rel == 2 and (to - d) & 3 in (1, 3)
    return False

def predict(lab, face, d):
    """The move gate_decide.model's label implies: FORWARD steps the way the group faces, TURN and TURN_ATTACK face d,
    BEHIND_TURN turns a quarter either way, ATTACK stays; WANDER/FORGET/SPECIAL are not predicted (None)."""
    if lab == 'FORWARD': return {('step', face)}
    if lab in ('TURN', 'TURN_ATTACK'): return {('turn', d)}
    if lab == 'BEHIND_TURN': return {('turn', (face + 1) & 3), ('turn', (face - 1) & 3)}
    if lab == 'ATTACK': return {('none', None)}
    return None

def main():
    snap, gi, budget, plan = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
    out = sys.argv[5] if len(sys.argv) > 5 else None
    todo = {}
    for item in filter(None, plan.split(';')):
        n, ks = item.split(':'); todo[int(n)] = [int(k, 16) for k in ks.split(',') if k]
    s = srv(snap); tb = s.read(0x10b2c, 64); p2start = s.read(A6 + 11322, 2048)
    used = 0; acts = []; frame_rng = lambda: struct.unpack('>H', s.read(A6 + 15530, 2))[0]

    def run(n):
        """Run n steps, handling every group action on the way."""
        nonlocal used
        left = n
        while left > 0:
            r = s('run', max_steps=left, until_pc=[THINK]); left -= r['steps']; used += r['steps']
            if r['reason'] != 'until': continue
            rec = s.reg('a0') & 0xffffff
            if rec != group_addr(s, gi): continue
            b = s.read(rec, 9); cx, cy, f5, typ = b[0], b[1], b[5], b[8]
            px, py = w16(s, 26), w16(s, 28); p2 = s.read(A6 + 11322 + cy * 64 + cx, 1)[0]
            rng = frame_rng(); step0 = r['step']
            ret = struct.unpack('>I', s.read(s.reg('a7'), 4))[0]
            r2 = s('run', max_steps=200000, until_pc=[ret]); left -= r2['steps']; used += r2['steps']
            assert r2['reason'] == 'until', r2
            a = group_addr(s, gi); b2 = s.read(a, 6)
            nx, ny, nf = b2[0], b2[1], b2[5] & 3
            if (nx, ny) != (cx, cy):
                d = [k for k, v in DXY.items() if v == (nx - cx, ny - cy)]
                move = ('step', d[0] if d else None)
            elif nf != f5 & 3: move = ('turn', nf)
            else: move = ('none', None)
            br = branch(cx, cy, f5, typ, px, py, p2)
            lab = model(cx, cy, f5 & 3, f5, typ, px, py, rng, p2, tb[typ])
            acts.append(dict(n=len(acts) + 1, step=step0, cell=(cx, cy), face=f5 & 3, f5=f5, p2=p2, party=(px, py),
                             br=br, lab=lab, typ=typ, rng=rng, ranged=tb[typ], move=move, after=(nx, ny, nf), f5after=b2[5]))
            todo_now = todo.pop(len(acts), None)
            if todo_now: pending.extend(todo_now)

    pending = list(todo.pop(0, []))
    while used < budget:
        if pending:
            k = pending.pop(0)
            s('kbd', bytes=[k]); run(60000); s('kbd', bytes=[k | 0x80]); run(300000)
            print(f'key {k:02x} -> party ({w16(s, 26)},{w16(s, 28)}) facing {DIRS[w16(s, 30) & 3]}  step {used}')
        else:
            run(min(60000, budget - used))
    if out: s('save', path=os.path.abspath(out))
    s.close()

    print('\nact  step       cell     face f5  plane2 (start) b0-2 b3-5 party    branch  model        move       after')
    tr = ok3 = ok0 = diff = ok3d = ok0d = 0; rep = rep0 = 0; ctl = []
    for a in acts:
        lo, hi = a['p2'] & 7, (a['p2'] >> 3) & 7
        mv = a['move'][0] + ('' if a['move'][1] is None else ' ' + DIRS[a['move'][1]])
        st = p2start[a['cell'][1] * 64 + a['cell'][0]]
        print(f"{a['n']:3d}  {a['step']:<10d} {str(a['cell']):8s} {DIRS[a['face']]}    {a['f5']:02x}  ${a['p2']:02x} (${st:02x})    {lo}    {hi}    "
              f"{str(a['party']):8s} {a['br']:7s} {a['lab']:12s} {mv:10s} ({a['after'][0]},{a['after'][1]}) {DIRS[a['after'][2]]} f5={a['f5after']:02x}")
        if a['br'] == 'trail' and a['move'][0] != 'none':
            tr += 1; m3 = fits(a['move'], hi, a['face']); m0 = fits(a['move'], lo, a['face']); ok3 += m3; ok0 += m0
            if lo != hi: diff += 1; ok3d += m3; ok0d += m0
        if a['br'] == 'trail' and lo != hi:
            # control: replay the model with the byte's bits 3-5 replaced by its bits 0-2 (the dig arrow)
            cx, cy = a['cell']; alt = (a['p2'] & 0xc7) | (lo << 3)
            lab0 = model(cx, cy, a['face'], a['f5'], a['typ'], *a['party'], a['rng'], alt, a['ranged'])
            p3, p0 = predict(a['lab'], a['face'], hi), predict(lab0, a['face'], lo)
            rep += a['move'] in (p3 or ()); rep0 += a['move'] in (p0 or ())
            ctl.append((a['n'], a['lab'], sorted(p3 or [], key=str), lab0, sorted(p0 or [], key=str), a['move']))
    print(f'\ntrail actions with a move: {tr}; follow bits 3-5: {ok3}/{tr}; follow bits 0-2 (control): {ok0}/{tr}')
    print(f'of those on cells where bits 3-5 != bits 0-2: {diff}; bits 3-5 {ok3d}/{diff}; bits 0-2 {ok0d}/{diff}')
    print(f'model replay on trail actions where the fields differ: observed move = prediction from bits 3-5 {rep}/{len(ctl)}, '
          f'from bits 0-2 {rep0}/{len(ctl)}')
    for c in ctl: print('  act %d: bits 3-5 -> %s %s; bits 0-2 -> %s %s; observed %s' % c)
    print(f"model label vs move: " + ', '.join(f"{a['n']}:{a['lab']}/{a['move'][0]}" for a in acts))

if __name__ == '__main__':
    main()
