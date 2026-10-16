"""route_tokenL.py <start.snap> <OUTDIR> [--upto=<leg>] [--from=<leg>]: Cadaver level 1, the token-L chain by natural joystick input (93rd pass, routeL).  Nothing poked.

Start: the health route's 27_out14.snap (route_health.py) (room 13, health 95, poison 0, tokens W and U held, F applied, SLEEP 570, CURE POISON 491).
Legs are explore.py commands (one snapshot reload per leg) with one addition: `I<oid>:<icon hex>` opens item <oid>'s panel through the Return grid and picks
the icon (routeH's item_icon(): explore.py's C/K lose their pulses once the rucksack holds 5 or more items; k = 0 RIGHT pulses is never tried).
An `I` word splits the leg: the words before it run through explore.py, then the item panel, then the rest.  `HAVE` asserts what each leg must leave in the rucksack.
Writes NN_<leg>.snap in OUTDIR and prints room / bbox / health / poison 2434(A5) / rucksack per leg; ends with `end room ...`."""
import sys, os
ARGS = [os.path.abspath(a) if a.endswith('.snap') or not a.startswith('--') else a for a in sys.argv[1:]]   # before env: lib/drv.py chdirs on import
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from explore import *
import explore
args = [a for a in ARGS if not a.startswith('--')]; flags = dict(a[2:].split('=', 1) for a in ARGS if a.startswith('--'))
start, outdir = args[0], args[1]; os.makedirs(outdir, exist_ok=True)

LEGS = [
    ('to14',      ['Z15:14', 'A14:95']),
    ('to15',      ['Z1f:15', 'A15:95']),
    ('to16',      ['Z1b:66', 'A16:95']),
    ('to18',      ['Z1c:23', 'A18:95']),
    ('to21',      ['Z26:20', 'A21:95', 'E26']),              # lane 16 stalls at y lead 78; entering room 21 sets $26 to ffff
    ('sleep21',   ['I570:d', 'F', 'B485', 'A21:95']),           # r21.0@24 sets 485 bit 0: without it room 22's entry SHOWs the monster 483 into room 21 (a touch drained 86 to 2)
    ('to23',      ['Z23:16', 'A23:95']),
    ('show405',   ['HR', 'O3', 'S200000', 'A23:95']),         # 404 (icons 3 10 11 6), event 5 SHOWs 405 at (32..34,21..23)
    ('take405',   ['GR:x>=41', 'GD:y>=27', 'O2', 'S100000', 'A23:95']),   # the walk south pushes 405 to y 28..30; probe from the north
    ('back21',    ['GU:y<=14', 'Z23:16', 'A21:95']),
    ('to22',      ['Z1d', 'A22:95']),                         # entry GOMOVEs the posts 695/696 down onto door $6f (gaps of 4-6 cells, hero 7)
    ('sleep22',   ['I570:d', 'F', 'A22:95', 'E25,6f']),        # r22.0@24 deletes 695/696 and clears $25; no XP
    ('to83',      ['Z6f:16', 'A83:95']),
    ('apply405',  ['GD:y>=21', 'GR:x>=69', 'HU', 'I405:c', 'S300000', 'E71', 'A83:95']),   # 406 event 18 (gate 405) clears $71
    ('to85',      ['Z71', 'A85:95']),
    ('take777',   ['GD:y>=28', 'GR:x>=40', 'HU', 'O2', 'S100000', 'A85:95']),
    ('apply777',  ['GU:y<=14', 'GL:x<=14', 'GD:y>=37', 'JD:30', 'S100000', 'GR:X>=9', 'GD:y>=53', 'WL:1:60000', 'I777:c', 'S300000', 'A85:95']),   # on slab 212 (z 16), y overlapping 374's 51..55 (374 at x 7 blocks a Down hold at x trail 7): 374 SHOWs the chains 134/148
    ('climb375',  ['S300000', 'HU', 'GU:y<=30', 'GR:x>=40', 'GD:Y>=48', 'GR:x>=65', 'GD:y>=56', 'JU:30', 'JU:30', 'GD:Y>=28', 'JU:30', 'A85:95']),
    ('pull134',   ['GL:x<=41', 'GD:y>=28', 'O7', 'S300000', 'A85:95']),       # from the lintel 106 (z 48): 134 GOMOVEs the block 373 off the pit
    ('to91',      ['GL:x<=36', 'GD:y>=30', 'S800000', 'HD', 'S2500000', 'A91:95']),   # region 1 of room 85 -> room 91 (3,6,110); the fall costs nothing
    ('to92',      ['GR:x>=41', 'HU', 'S2500000', 'A92:95']),                   # region 1 of room 91 -> room 92 (5,2,100)
    # room 92: hunters 808 (POISON 10,40,10 on touch) and, once lever 399 has lifted the wall 400, 807 (-3 per touch frame); both chase, x first
    ('take643',   ['GL:X<=8', 'GD:y>=41', 'O2', 'A92:95']),
    ('lever399',  ['WL:1:60000', 'O7', 'A92:95']),                                # SHOWs the touch teleports 401-403 at (41..43,9..11), z 32..112
    ('take702',   ['GD:y>=46', 'O2', 'A92:95']),
    ('out92',     ['GD:y>=55', 'GR:x>=42', 'GU:y<=13', 'J-:30', 'S1500000', 'A91:80']),   # a vertical jump under 401 (top z 32): 807 touches on the way up
    ('lever398',  ['GL:x<=20', 'GU:y<=24', 'HL', 'HU', 'O7', 'S300000', 'A91:80']),     # west first: region 1 (34..46,10..22) teleports back to room 92; SHOWs 395-397 at (5..7,37..39), z 16..96
    ('to85b',     ['HD', 'S300000', 'A85:80']),                                   # touch 395 -> room 85 (7,7,0)
    ('to83b',     ['GL:X<=48', 'GU:y<=28', 'GL:x<=14', 'Z71', 'A83:80']),
    ('to22b',     ['Z6f:24', 'A22:80']),                                          # lanes 16 and 20 stall in room 83
    ('to21b',     ['Z1d', 'A21:80']),
    ('apply643',  ['GU:y<=16', 'GL:X<=8', 'I643:c', 'S300000', 'E26', 'A21:80']),   # 485 event 18 (gate 643) clears $26; HL stalls short at x trail 10-11, a goto reaches 8
    ('to18b',     ['Z26:16', 'A18:80']),
    # room 43 is not joined to room 21: 18 -> 16 -> 15 (lever 171 lifts the wall 160 off door $18) -> 17 (stairs 92-89 up to the high door $3d) -> 44 -> 43
    ('to16b',     ['Z1c', 'A16:80']),
    ('to15b',     ['Z1b', 'A15:80']),
    ('lever171',  ['GR:x>=77', 'GU:Y<=8', 'O4', 'S1000000', 'A15:80']),       # icons 4 11 6; GR:x>=79 crosses door $22 into room 14
    ('to17',      ['GL:x<=34', 'HU', 'S100000', 'A17:80']),
    ('climb17',   ['GR:x>=75', 'GU:y<=20', 'JL:30', 'GR:x>=66', 'JL:30', 'GR:x>=58', 'JL:30', 'GR:x>=50', 'JL:30', 'A17:80']),   # 4 jumps (z 16, 32, 48, 64): each needs a run-up gap of about 5 cells, overhanging the step
    ('to44',      ['Z3d', 'A44:80']),
    ('to43',      ['Z3c', 'A43:80']),
    ('apply702',  ['GU:y<=71', 'GL:X<=8', 'I702:c', 'S1000000', 'A43:80']),     # 701 event 18 (gate 702): the pillars 707/708 slide south to y 71..73
    ('walk709',   ['GU:y<=68', 'GR:x>=22', 'GU:Y<=23', 'GR:x>=20', 'GU:y<=22', 'GL:X<=11', 'A43:80']),   # clear of 707's new row, then through the gap x 16..22; region 1 drops the crushers 597-599 to z 20 at y 13..15
    ('take709',   ['O2', 'S100000', 'A43:80']),
]
HAVE = {'take405': [405], 'take777': [777], 'take643': [643], 'take702': [702], 'take709': [709]}
GONE = {'apply405': [405], 'apply777': [777], 'apply643': [643], 'apply702': [702]}


def item_icon(inp, out, oid, icon, ks=range(1, 9)):
    """routeH/route_health.py item_icon(): Return grid, k RIGHT pulses, FIRE, then icon; k searched on fresh loads of `inp`, the first that opens oid's panel and answers"""
    from drv import cur_icon
    for k in ks:
        r = Repl(inp); t = Tally(r); tap(r, t, 0x1c)
        for _ in range(k): pulse(r, t, RIGHT)
        t.joy(FIRE); t.run(40000); t.joy(0); t.run(90000)
        if r.w(A5 + 1236) == oid:
            try:
                pick_icon_id(r, t, icon); t.run(100000)
                print('   item %d icon %x via k=%d, sel %s' % (oid, icon, k, r.a5(1262, 2).hex()), flush=True); r.snap(out); r.close(); return k
            except AssertionError: pass
        r.close()
    raise AssertionError(('item panel', oid, icon))


def run_leg(cur, out, cmds, tmp):
    seg = []; n = 0
    for c in cmds + [None]:
        if c is None or c[0] == 'I':
            if seg or c is None:
                nxt = out if c is None else '%s.seg%d.snap' % (out, n); n += 1
                res = explore.run(cur, nxt, seg, tmp=tmp); cur = nxt; seg = []
            if c is not None:
                oid, ic = c[1:].split(':'); nxt = '%s.seg%d.snap' % (out, n); n += 1
                item_icon(cur, nxt, int(oid), int(ic, 16)); cur = nxt
        else: seg.append(c)
    return res


def state(out):
    r = Repl(out); t8 = type8(r); ruck = [a for a, b in t8['recs'][:t8['count']]]
    s = (r.w(ROOM), pos(r), zz(r), hp(r), r.b(A5 + 2434), r.l(A5 + 1192), ruck); r.close(); return s


names = [l[0] for l in LEGS]; i0 = names.index(flags['from']) if 'from' in flags else 0
cur = start if i0 == 0 else os.path.join(outdir, '%02d_%s.snap' % (i0, names[i0 - 1]))
for n, (name, cmds) in enumerate(LEGS[i0:], i0 + 1):
    out = os.path.join(outdir, '%02d_%s.snap' % (n, name))
    print('== leg %d %s: %s' % (n, name, ' '.join(cmds)), flush=True)
    run_leg(cur, out, cmds, os.path.join(outdir, '_scratch_%s' % name))
    room, p, z, h, ps, xp, ruck = state(out)
    for o in HAVE.get(name, []): assert o in ruck, (name, 'missing', o, ruck)
    for o in GONE.get(name, []): assert o not in ruck, (name, 'still held', o, ruck)
    print('   -> room %d pos %s z %s health %d poison %d xp %d ruck %s' % (room, p, z, h, ps, xp, ruck), flush=True)
    cur = out
    if flags.get('upto') == name: break
print('end room %d health %d poison %d' % (room, h, ps), flush=True)
