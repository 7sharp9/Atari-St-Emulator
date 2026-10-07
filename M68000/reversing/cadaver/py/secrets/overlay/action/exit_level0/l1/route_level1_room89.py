"""route_level1_room89.py <end_room90.snap> <OUTDIR> [--upto=<leg name>]: level 1 from room 90 (health 60) to room 89 by natural joystick input (92nd pass).  Nothing poked.

The 91st-pass chain (mechanics.md section 12) is a door graph; driving it shows what its legs hide.  This script is the part that is driven, leg by leg (`explore.py` commands, one snapshot
reload per leg, an assertion per leg):
  lever562   room 90's lever 562 deletes the pillars 213 and 214 of room 12 (the way back west is free only after it);
  to29       door $7b, $7a, then room 29: jump onto the block 558 (the item 493 lies on it), step off west, TAKE 493 (teleports to room 30);
  room30     lever puzzle: levers 201, 202, 203, 201 (each pull arms the next; three own-parts make VAR 5 = 3), then icon 4 on object 222 lifts the gate 126; costs 10 (the mover 421
             after the third own-part) and 5 (the contact trap 636 on the way to 222); door $38 to room 2 from a lane with y lead <= 22;
  to19       rooms 2, 3, 13, 14, 15, 16, 18, 19 by door lanes (room 13: y lead 14, room 14: north strip, room 15: avoid the pit region x 8..24 y 32..48);
  stamina    object 521 in room 19 is a STAMINA with five doses of +10 (icon 9), the fifth consumes it: 45 -> 95;
  sleep      SLEEP scroll 570 on the floor of room 14, between the four plates (each plate step spawns flyers that cost 20 per touch: 95 -> 55), then back to room 1;
  room1      room 1's region 1 (x 0..47, y 0..15) teleports the hero to (4,7) unless object 659's bit 0 is set, which a cast of SLEEP in room 1 does (r1.0@24, +26 XP); door $0f -> room 89;
  token      room 89: the token F (223) is taken, and applied to the slot 206 (VAR 9 = 1).
Then the tokens U (room 28, left by door $33: the arrival at door $2f overlaps the trap 635 and the move is refused) and W (room 14, from the east at y lead 50, no plate hit).  Ends in room 13 with health 35 and the rucksack 570, 680, 224, 338, 493 (F applied).  The lever 27 of room 89 is on a shelf at z 64..83 reached only from room 9's door $0e: see mechanics.md section 12.
Writes NN_<leg>.snap in OUTDIR and ends with `end room 89 ...`."""
import sys, os
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from explore import run
args = [a for a in sys.argv[1:] if not a.startswith('--')]; flags = [a for a in sys.argv[1:] if a.startswith('--')]
start, outdir = os.path.abspath(args[0]), os.path.abspath(args[1]); os.makedirs(outdir, exist_ok=True)
upto = next((f.split('=')[1] for f in flags if f.startswith('--upto=')), None)
os.environ.setdefault('CAD_OUT', os.path.join(outdir, '_scratch'))

LEGS = [
    ('lever562',  ['HU', 'GR:x>=24', 'O7', 'S500000', 'A90']),
    ('to12',      ['GD:y>=20', 'HL', 'S150000', 'A12']),
    ('to31',      ['GL:x<=22', 'HD', 'S150000', 'A31']),
    ('to29',      ['HL', 'S150000', 'A29']),
    ('block558a', ['GD:y>=58', 'HL', 'A29']),
    ('block558b', ['GR:x>=79', 'JL:30', 'A29']),
    ('block558c', ['GL:x<=58', 'S200000', 'A29']),
    ('take493',   ['GR:x>=59', 'O2', 'S100000', 'A30:60']),
    ('lever1',    ['HU', 'GL:x<=22', 'HU', 'O7', 'S200000', 'A30:60']),
    ('lever2',    ['GR:x>=36', 'HU', 'O7', 'S200000', 'A30:60']),
    ('lever3',    ['GR:x>=50', 'HU', 'O7', 'S200000', 'A30:60']),
    ('lever4',    ['GL:x<=22', 'HU', 'O7', 'S200000', 'A30:50']),
    ('to222',     ['GR:x>=23', 'GD:y>=32', 'HL', 'A30:45']),
    ('gate126',   ['O4', 'S400000', 'A30:45']),
    ('door38',    ['S500000', 'GU:y<=22', 'HL', 'S100000', 'A2:45']),
    ('to3',       ['Z04', 'A3:45']),
    ('to13',      ['Z12:14', 'A13:45']),
    ('to14',      ['Z15:14', 'A14:45']),
    ('to15',      ['Z1f:15', 'A15:45']),
    ('to16',      ['Z1b:66', 'A16:45']),
    ('to18',      ['Z1c:23', 'A18:45']),
    ('to19',      ['Z1e:16', 'A19:45']),
    ('stamina',   ['HD', 'O9', 'O9', 'O9', 'O9', 'O9', 'S200000', 'A19:95']),
    ('back18',    ['Z1e', 'A18:95']),
    ('back16',    ['Z1c', 'A16:95']),
    ('back15',    ['Z1b:66', 'A15:95']),
    ('back14',    ['GR:x>=32', 'Z1f:15', 'A14:95']),
    ('scroll570a', ['GR:x>=38']),
    ('scroll570b', ['GD:y>=33', 'O2', 'S300000', 'A14:50']),
    ('back13',    ['GU:y<=17', 'Z15:15', 'A13:50']),
    ('back3',     ['Z12:14', 'A3:50']),
    ('back2',     ['Z04', 'A2:50']),
    ('back1',     ['Z02', 'A1:50']),
    ('sleep',     ['C570', 'Kd', 'F', 'A1:50']),
    ('to89',      ['Z0f:23', 'A89:50']),
    ('tokenF_a',  ['GU:y<=36', 'GR:x>=37', 'O2', 'A89:50']),
    ('tokenF_b',  ['GL:x<=14', 'C223', 'Kc', 'S300000', 'B206', 'A89:50']),
    # tokens U (room 28) and W (room 14): the way to the slot needs all four (F, W, U, L), then door $0b opens
    ('to1',       ['HD', 'A1:50']),
    ('to2',       ['Z02:23', 'A2:50']),
    ('to30',      ['Z38', 'A30:50']),
    ('to28',      ['Z2f:11', 'A28:50']),
    ('tokenU',    ['GR:x>=23', 'GD:y>=48', 'O2', 'S100000', 'A28:50']),
    ('out28',     ['S2500000', 'Z33:42:60000', 'A30:50']),
    ('toRoom14',  ['Z38:21', 'A2:40', 'Z04', 'A3:40', 'Z12:14', 'A13:40', 'Z15:14', 'A14:40']),
    ('tokenW',    ['GD:y>=50', 'GL:x<=58', 'O2', 'S200000', 'A14:40']),
    ('out14',     ['GR:x>=79', 'Z15:14', 'A13:30']),
]

cur = start; n = 0
for name, cmds in LEGS:
    n += 1; out = os.path.join(outdir, '%02d_%s.snap' % (n, name))
    print('== leg %d %s: %s' % (n, name, ' '.join(cmds)), flush=True)
    room, p, h, ps = run(cur, out, cmds, tmp=os.path.join(outdir, '_scratch_%s' % name))
    print('   -> room %d pos %s health %d poison %d' % (room, p, h, ps), flush=True)
    cur = out
    if upto == name: break
print('end room %d health %d' % (room, h), flush=True)
