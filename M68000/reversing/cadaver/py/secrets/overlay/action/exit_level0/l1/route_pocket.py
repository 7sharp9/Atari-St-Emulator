"""route_pocket.py <start.snap> <OUTDIR> [--upto=<leg>] [--from=<leg>]: Cadaver level 1, room 43 back to room 89, the four tokens on the slot 206, rooms 9 and 10,
the shelf of room 89, lever 27 and door $01 into room 4, and room 4's lift pushed over the pit and raised to the high door $08 into room 6, by natural joystick input.  Nothing poked.

Start: route_tokenL.py's 42_take709.snap (room 43, health 89, poison 0, tokens L 709, W 224, U 338 held, F applied: VAR 9 = 1).
End: 33_to6.snap, room 6 at bottom z 64 (health 89, poison 0, VAR 9 = 4, 380's bit 0 set).  Room 4's entry block r4.0@6 shuts $01 again (its opener, lever 27,
is in room 89); the high doors $07/$08 (x 60..83, z 64..111) are crossed by a walk only with x wholly inside 60..83 and bottom z 63..82, which the lift gives once it has
been pushed east over the pit while lowered (legs 29-32; mechanics.md section 12, "Room 4 and the pocket").  25_drop89.snap (room 89, $01 open) is the branch point
for routes that avoid room 4.
Legs are explore.py commands (one snapshot reload per leg) plus three words of this script, each run as its own reload segment:
  I<oid>:<icon hex>   the item panel through the Return grid (route_tokenL.py's item_icon, with the grid's second row: see SEQS)
  =<axis><n>          tap until the bbox axis (x, y, X, Y as in explore.py's goto) reads exactly n
  o<icon hex>:<steps> explore.py's O with <steps> run after the pick instead of 200,000
HAVE/GONE assert the rucksack after a leg, VAR9 the tokens applied (VAR 9 = 2282(A5) + 9), OPEN the door words that must read 0, BIT0 an object's record +3 bit 0,
ZMIN the hero's bottom z.  Writes NN_<leg>.snap in OUTDIR and prints room / bbox / z / health / poison 2434(A5) / XP / rucksack / VAR 9 / door words per leg.
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
    # room 43 -> 44 -> 17 (the high door $3d lands on the platform 79/80 at z 64)
    ('to44',      ['GR:X>=16', 'GD:y>=66', 'Z3c', 'N', 'A44:89']),            # east of 699 (x 13..15, y 53..55), then west of 707 (moved to y 71..73) on the portal's default lane
    ('to17',      ['Z3d', 'N', 'A17:89']),
    ('down17',    ['GR:X>=64', 'S300000', 'GD:Y>=24', 'GL:x<=60', 'N', 'A17:89']),   # walk east off the stair 89-92 (falls step by step to the floor)
    ('to15',      ['Z18:60', 'N', 'A15:89']),                                     # door $18 (lever 171 opened it on the way out)
    ('to14',      ['Z1f:15', 'N', 'A14:89']),
    ('to13',      ['GU:y<=17', 'GR:x>=76', 'GD:y>=40', 'Z16', 'N', 'A13:89']),    # door $16, not $15: arriving by $15 the creature 912 appears at (17,17) and takes 50 at once
    ('to3',       ['Z13:44', 'N', 'A3:89']),                                      # y 38..44 meets none of the touch blocks 645-649
    ('to2',       ['Z04', 'N', 'A2:89']),
    ('to1',       ['Z02', 'N', 'A1:89']),
    ('to89',      ['Z0f:23', 'N', 'A89:89']),                                     # region 1 of room 1 is off (SLEEP cast there, 659 bit 0)
    ('stand206',  ['GU:y<=36', 'GL:x<=14', 'N', 'A89:89']),                       # facing west, the slot 206 (x 7, y 35..39, z 25..35) in front
    ('applyW',    ['I224:c', 'S300000', 'N', 'A89:89']),
    ('applyU',    ['I338:c', 'S300000', 'N', 'A89:89']),
    ('applyL',    ['I709:c', 'S300000', 'E0b', 'N', 'A89:89']),                   # the fourth application: o206.*@18 YOUR WAY IS CLEAR, door $0b
    # room 9 (first entry +26 XP): the lift 140 and the high door $0e to the shelf of room 89
    ('to9',       ['Z0b', 'N', 'A9:89']),
    ('lift140',   ['GU:y<=38', 'GL:X<=8', 'O7', 'N', 'A9:89']),                   # 393 (x 4..7, y 35..39, icons 7 11 6) GOMOVEs the block 140 from z 0..7 to 56..63 (about 1.9M steps), level with the cap 566
    ('to10',      ['S2000000', 'GD:y>=62', 'Z0a', 'N', 'A10:89']),
    ('climb10',   ['GU:y<=36', 'GL:X<=28', 'GU:y<=20', 'JR:30', 'GL:X<=37', 'JR:30', 'GL:X<=45', 'JR:30', 'GL:X<=53', 'JR:30', 'N', 'A10:89']),   # the stair 31, 30, 29, 28 (z 16..64), mirror of room 17's: west along y 29..35 (the steps are solid below), four jumps east
    ('to9high',   ['Z0c', 'S300000', 'N', 'A9:89']),                              # the arrival (8..14,14..20) z 64 is on 140: before the lift it falls to z 20
    ('take391',   ['O2', 'S100000', 'N', 'A9:89']),                               # 391 (15..21,13..18) rode up on 140 and blocks the only lane to $0e (y 7..13): taken
    ('drink480',  ['GD:y>=24', 'WR:1:40000', 'O9', 'S200000', 'N', 'A9:89']),     # 480 (icons 2 9 10 11 6) drunk: event 5 sets 380's bit 0 (room 6's post: YOU ARE NOT STRONG ENOUGH TO MOVE THE POST while clear)
    ('to89high',  ['Z0e:10', 'N', 'A89:89']),                                     # onto the cap 17 at z 64
    ('lever27',   ['GR:x>=45', 'S200000', 'HU', 'O7', 'S300000', 'E01', 'N', 'A89:89']),   # down onto the caps 19/18 (z 56); 27 (icons 7 11 6) from the south clears door $01
    ('jump17',    ['GL:x<=34', 'JL:30', 'N', 'A89:89']),                          # the caps 19/18 have no way down (poles 773-776, 675 at z 64..127, gaps of 5): jump back onto 17
    ('drop89',    ['GR:x>=27', '=x28', 'GD:y>=30', 'S600000', 'N', 'A89:89']),   # off 17's south edge in the one 7-wide gap x 22..28 (675 at 19..21, 775 at 29..31); the fall costs nothing
    ('to4',       ['Z01', 'N', 'A4:89']),                                         # room 4's entry block sets $01 back to ffff
    # room 4 (80 x 24): the pit region 1 (66..78, 10..22, z 2..4; TELEPORT to room 94) fills the east half, the doors on (high $07, $08 at x 60..83, z 64) are above it;
    # the lift 2 (40..55, 8..23) is at z 56..63 and each operate of 231 or 232 runs one leg of its mover program (z only): down to z 6..13, up again (about 1.25M steps each);
    # lowered, it is pushed like any block, and over the pit (64..79, the floor mark 381) it stays out of the pit region's z 2..4
    ('stand231',  ['GR:x>=31', 'HU', 'HL', 'N', 'A4:89']),                         # (24..30, 7..13) facing west: 231 (19..23, 4..7, icons 7 11 6) in front
    ('lower2',    ['O7', 'S1200000', 'N', 'A4:89']),                              # the lift down to z 6..13
    ('push2',     ['GD:y>=18', 'GR:x>=63', 'N', 'A4:89']),                        # push the lowered lift east from (24..30, 13..19) to x 64..79 over the pit; the hero stops at (57..63), outside the pit region
    ('onlift',    ['GL:x<=55', 'JR:30', 'N', 'A4:89']),                           # an 8-cell run-up, RIGHT jump onto the lift top (bottom z 14)
    ('at232',     ['GU:y<=13', 'GR:x>=79', 'N', 'A4:89']),                        # to the north wall; east until lever 232 (75..79, 4..7, z 16..35) stops the hero at x lead 74
    ('raise232',  ['WR:2:20000', 'O7', 'S1500000', 'N', 'A4:89']),                # face 232, operate it: the lift rises to z 56..63 with the hero on it (bottom z 64, x 68..74)
    ('to6',       ['HD', 'N', 'A6:89']),                                          # south along the lift through $08 (60..83, y 24..30, z 64..111) into room 6; HU from raise232 goes through $07 to room 5
]
HAVE = {'take391': [391]}
GONE = {'applyW': [224], 'applyU': [224, 338], 'applyL': [224, 338, 709]}
VAR9 = {'to44': 1, 'stand206': 1, 'applyW': 2, 'applyU': 3, 'applyL': 4}
OPEN = {'applyL': [0x0b], 'lever27': [0x01]}
BIT0 = {'drink480': [380]}                 # record +3 bit 0 set
ZMIN = {'to9high': 56, 'take391': 56, 'drink480': 56, 'to89high': 56, 'onlift': 14, 'raise232': 64, 'to6': 64}   # hero bottom z at least (on the raised block / the shelf)


# The Return grid is 4 cells wide: with 7 items RIGHT pulses only cycle the first row (cells 0-3: 709, 570, 680, 491 here) and a DOWN reaches the second row
# (224, 338, 493).  The first pulse after Return is lost (R and D alone both leave the cursor 2122(A5) at cell 0), so 'RD' is cell 4 and 'RDR' cell 5.
SEQS = ['R' * k for k in range(1, 5)] + ['RD' + 'R' * k for k in range(0, 4)]


def item_icon(inp, out, oid, icon, seqs=SEQS):
    """route_tokenL.py item_icon() with the second grid row: Return, a pulse sequence, FIRE, then icon; the sequence is searched on fresh loads of `inp`,
    the first that opens oid's panel and answers.  A panel opened with no pulse ignores the joystick (route_health.py), so the empty sequence is not tried."""
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


def exact(inp, out, ax, n, tapn=50000, tries=12):
    """`=<axis><n>` (axis x/y/X/Y as in explore.py's goto): tap toward bbox[axis] == n (hold `tapn` steps, release 40,000) until it reads n; a goto overshoots
    by a cell either way, which the 7-wide gap of room 89's shelf does not allow"""
    i = 'xyXY'.index(ax); r = Repl(inp)
    for _ in range(tries):
        v = pos(r)[i]
        if v == n: break
        d = (RIGHT if v < n else LEFT) if i in (0, 2) else (DOWN if v < n else UP)
        joy(r, d); r.cmd('s %d' % tapn); joy(r, 0); r.cmd('s 40000')
    assert pos(r)[i] == n, ('exact', ax, n, pos(r))
    print('   =%s%d %s' % (ax, n, st(r)), flush=True); r.snap(out); r.close()


def operate(inp, out, icon, post):
    """`o<icon hex>:<steps>`: explore.py's O (panel of the object in front, pick the icon) with `steps` run after it instead of 200,000: the lift ride needs
    the hero moving within about 100,000 steps of the operate"""
    r = Repl(inp); t = Tally(r); open_panel(r, t); pick_icon_id(r, t, icon); t.run(post)
    print('   o%x:%d %s' % (icon, post, st(r)), flush=True); r.snap(out); r.close()


def run_leg(cur, out, cmds, tmp):
    seg = []; n = 0
    for c in cmds + [None]:
        if c is not None and c[0] == 'o':
            if seg: nxt = '%s.seg%d.snap' % (out, n); n += 1; explore.run(cur, nxt, seg, tmp=tmp); cur = nxt; seg = []
            nxt = '%s.seg%d.snap' % (out, n); n += 1; operate(cur, nxt, *[int(v, 16) if i == 0 else int(v) for i, v in enumerate(c[1:].split(':'))]); cur = nxt
            continue
        if c is not None and c[0] == '=':
            if seg: nxt = '%s.seg%d.snap' % (out, n); n += 1; explore.run(cur, nxt, seg, tmp=tmp); cur = nxt; seg = []
            nxt = '%s.seg%d.snap' % (out, n); n += 1; exact(cur, nxt, c[1], int(c[2:])); cur = nxt
            continue
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
    s = dict(room=r.w(ROOM), pos=pos(r), z=zz(r), hp=hp(r), poison=r.b(A5 + 2434), xp=r.l(A5 + 1192), ruck=ruck, var9=r.b(A5 + 2282 + 9),
             doors={d: r.w(0x6d35a + 8 * d + 2) for d in (0x01, 0x0b, 0x0e)},
             bit0={o: (r.b(live_rec(r, o) + 3) & 1 if live_rec(r, o) else None) for o in (380,)})
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
    if name in VAR9: assert s['var9'] == VAR9[name], (name, 'VAR 9', s['var9'])
    for d in OPEN.get(name, []): assert s['doors'][d] == 0, (name, 'door shut', d, s['doors'])
    for o in BIT0.get(name, []): assert s['bit0'][o] == 1, (name, 'bit 0 clear', o)
    if name in ZMIN: assert s['z'][1] >= ZMIN[name], (name, 'z', s['z'])
    print('   -> room %d pos %s z %s health %d poison %d xp %d ruck %s var9 %d doors %s' % (
        s['room'], s['pos'], s['z'], s['hp'], s['poison'], s['xp'], s['ruck'], s['var9'], {'%02x' % d: '%04x' % w for d, w in s['doors'].items()}), flush=True)
    cur = out
    if flags.get('upto') == name: break
print('end room %d health %d poison %d var9 %d' % (s['room'], s['hp'], s['poison'], s['var9']), flush=True)
