"""route_pocket2.py <start.snap> <OUTDIR> [--upto=<leg>] [--from=<leg>]: Cadaver level 1, room 6 (the Side Chamber): the post 380 pushed under the caps,
the flask 219 drunk and the key 251 taken, the keyhole 698 opened and door $10 crossed into room 1, by natural joystick input.  Nothing poked.

Start: route_pocket.py's 33_to6.snap (room 6, on the ledge 392 at bottom z 64, health 89, the STRENGTH potion 480 drunk in leg drink480).
End: NN_to1.snap, room 1, health 189, key 251 used on 698.

The push rule (mechanics.md section 3, "Pushing"): a walk blocked by a non-solid object runs $ed5a, which charges each object it would move (and each object those
would move) its template weight byte 13 against the hero's strength 2144(A5), and refuses the whole push when the sum exceeds it.  The post weighs 140 and the
strength is 50, or 199 from 480's drink until timer 40 ends it, 7.0 to 7.5M steps after 33_to6.snap; so every push of the post sits in the first legs, and the
key (whose fall from z 64 is slow) is knocked off last.  Geometry (section 12, "The pocket's rooms"): each of the caps 162, 164, 166 GOMOVEs its item +8 in x on
the post's touch, which a push of the post west into the cap stack gives; the item falls to the floor only if the post's y band does not cover its landing cell:
flask 219 lands at (18..20, 57..59) with the post at y 60..68, key 251 at (19..21, 74..76) with the post at y 64..72, and the key is taken from the lane y 73..79,
so the post must stand at exactly y 64..72 for the key.  The flask is pushed ahead of a walk, and pushing it into the post moves both (weight 143), so leg
flask stops on the post's position, not on the hero's.
Legs are explore.py commands (one snapshot reload per leg) plus I<oid>:<icon hex> (route_pocket.py's item panel through the Return grid, its own reload).
HAVE/GONE assert the rucksack after a leg, POST the post's placement rect, HP a minimum health, STRENGTH the strength word 2144(A5).
The repo is found from M68000_ROOT or by walking up to the directory holding tools/rdis.py; the l1/ scripts are imported from there."""
import sys, os
ARGS = [os.path.abspath(a) if a.endswith('.snap') or not a.startswith('--') else a for a in sys.argv[1:]]   # before the import: lib/drv.py chdirs on import


def _root():
    if os.environ.get('M68000_ROOT'): return os.environ['M68000_ROOT']
    d = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(d, 'tools', 'rdis.py')):
        assert os.path.dirname(d) != d, 'repo root (tools/rdis.py) not found: set M68000_ROOT'
        d = os.path.dirname(d)
    return d


ROOT_ = _root(); os.environ.setdefault('M68000_ROOT', ROOT_)
sys.path.insert(0, os.path.join(ROOT_, 'reversing/cadaver/py/secrets/overlay/action/exit_level0/l1'))
from explore import *
import explore
args = [a for a in ARGS if not a.startswith('--')]; flags = dict(a[2:].split('=', 1) for a in ARGS if a.startswith('--'))
start, outdir = args[0], args[1]; os.makedirs(outdir, exist_ok=True)

LEGS = [
    # the post (70..78, 20..28, z 0..53, against the east wall) is pushed from its north-east corner; the floor north of it is reached under the ledge
    ('floor6',   ['S200000', 'GL:x<=63', 'GD:y>=17', '=y19', 'GR:x>=79', 'PDL:380:Y>=60', 'N', 'A6:89']),   # off the ledge's west edge, east along y 13..19
                                                                                                         # (a y lead of 20 meets the post and stalls), DOWN+LEFT
    ('west6',    ['GR:x>=46', 'GD:y>=66', 'PL:380:X<=16', 'WL:3:20000', 'N', 'A6:89']),   # post (30..38, 60..68) west to the caps: 164 GOMOVEs the flask
    ('north6',   ['GU:y<=55', 'GL:x<=23', 'N', 'A6:89']),                                  # round to the post's north side while the flask falls
    ('flask',    ['PD:380:Y>=63', 'Q', 'N', 'A6:89']),                                     # the flask is pushed into the post; both move, to y 63..71
    ('drink',    ['O9', 'PD:380:Y>=64', 'N', 'A6:189']),                                   # STAMINA +100, then the post one cell on to y 64..72
    ('key6',     ['GR:x>=32', 'GD:y>=70', 'HL', 'N', 'A6:189']),                           # west into 162: the key GOMOVEs (the strength's last use)
    ('take251',  ['GD:y>=79', 'S600000', 'HL', 'Q', 'O2', 'S100000', 'N', 'A6:189']),      # the key lands at (19..21, 74..76); the walk pushes it to the column
    ('hole',     ['GR:x>=32', 'GU:y<=17', '=y14', 'GL:x<=23', 'WU:1:20000', 'Q', 'N', 'A6:189']),   # (16..22, 8..14) facing up: the keyhole 698 (19..23, 7, z 24..39)
                                                                                                    # in front; a y trail of 7 meets 698's box and stalls
    ('apply251', ['I251:c', 'S300000', 'E10', 'N', 'A6:189']),
    ('to1',      ['Z10', 'N', 'A1:189']),
]
HAVE = {'take251': [251]}
GONE = {'drink': [219], 'apply251': [251]}
POST = {'floor6': (38, 68, 30, 60), 'west6': (24, 68, 16, 60), 'drink': (24, 72, 16, 64), 'key6': (24, 72, 16, 64)}
HP = {'drink': 189}
STRENGTH = {'key6': 199}
OPEN = {'apply251': [0x10]}


# route_pocket.py's Return-grid item panel (its docstring: copy these helpers or move them into explore.py)
SEQS = ['R' * k for k in range(1, 5)] + ['RD' + 'R' * k for k in range(0, 4)]


def item_icon(inp, out, oid, icon, seqs=SEQS):
    for seq in seqs:
        r = Repl(inp); t = Tally(r); tap(r, t, 0x1c)
        for ch in seq: pulse(r, t, {'R': RIGHT, 'D': DOWN}[ch])
        t.joy(FIRE); t.run(40000); t.joy(0); t.run(90000)
        if r.w(A5 + 1236) == oid:
            try:
                pick_icon_id(r, t, icon); t.run(100000)
                print('   item %d icon %x via %s, sel %s' % (oid, icon, seq, r.a5(1262, 2).hex()), flush=True); r.snap(out); r.close(); return seq
            except AssertionError: pass
        r.close()
    raise AssertionError(('item panel', oid, icon))


def run_leg(cur, out, cmds, tmp):
    seg = []; n = 0
    for c in cmds + [None]:
        if c is None or c[0] == 'I':
            if seg or c is None:
                nxt = out if c is None else '%s.seg%d.snap' % (out, n); n += 1
                explore.run(cur, nxt, seg, tmp=tmp); cur = nxt; seg = []
            if c is not None:
                oid, ic = c[1:].split(':'); nxt = '%s.seg%d.snap' % (out, n); n += 1
                item_icon(cur, nxt, int(oid), int(ic, 16)); cur = nxt
        else: seg.append(c)


def state(out):
    r = Repl(out); t8 = type8(r); ruck = [a for a, b in t8['recs'][:t8['count']]]
    s = dict(room=r.w(ROOM), pos=pos(r), z=zz(r), hp=hp(r), poison=r.b(A5 + 2434), xp=r.l(A5 + 1192), ruck=ruck, strength=r.w(A5 + 2144),
             post=orect(r, 380) if r.w(ROOM) == 6 else None, doors={d: r.w(0x6d35a + 8 * d + 2) for d in (0x10,)})
    r.close(); return s


names = [l[0] for l in LEGS]; i0 = names.index(flags['from']) if 'from' in flags else 0
cur = start if i0 == 0 else os.path.join(outdir, '%02d_%s.snap' % (i0, names[i0 - 1]))
for n, (name, cmds) in enumerate(LEGS[i0:], i0 + 1):
    out = os.path.join(outdir, '%02d_%s.snap' % (n, name))
    print('== leg %d %s: %s' % (n, name, ' '.join(cmds)), flush=True)
    run_leg(cur, out, cmds, os.path.join(outdir, '_scratch_%s' % name))
    s = state(out)
    for o in HAVE.get(name, []): assert o in s['ruck'], (name, 'missing', o, s['ruck'])
    for o in GONE.get(name, []): assert o not in s['ruck'], (name, 'still held', o, s['ruck'])
    if name in POST: assert s['post'] == POST[name], (name, 'post', s['post'])
    if name in HP: assert s['hp'] >= HP[name], (name, 'health', s['hp'])
    if name in STRENGTH: assert s['strength'] == STRENGTH[name], (name, 'strength', s['strength'])
    for d in OPEN.get(name, []): assert s['doors'][d] == 0, (name, 'door shut', d, s['doors'])
    print('   -> room %d pos %s z %s health %d poison %d xp %d strength %d post %s ruck %s doors %s' % (
        s['room'], s['pos'], s['z'], s['hp'], s['poison'], s['xp'], s['strength'], s['post'], s['ruck'],
        {'%02x' % d: '%04x' % w for d, w in s['doors'].items()}), flush=True)
    cur = out
    if flags.get('upto') == name: break
print('end room %d health %d poison %d' % (s['room'], s['hp'], s['poison']), flush=True)
