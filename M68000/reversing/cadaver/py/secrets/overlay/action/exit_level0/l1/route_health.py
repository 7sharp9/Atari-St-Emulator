"""route_health.py <24_back18.snap> <OUTDIR> [--upto=<leg>] [--from=<leg>]: the health legs of the room-89 route (s92/run5, route_level1_room89.py),
replayed by natural input from its leg 24 (room 18, health 95, after the STAMINA 521).  Nothing poked.
Changes against the old route:
  cure        door $21 to room 20, take the CURE POISON 491 (no health lost), back to room 18;
  back16      a 600,000-step stand in room 18 first: without it the hero is poisoned on the north lane (the creature table phase changed with the detour;
              waits 450,000-650,000 are clean except 525,000, 0-425,000 and 750,000-3,000,000 poison);
  scroll570   SLEEP 570 taken from the west at y lead 38 (x lead 36, facing right) instead of from the north at x lead 38: the flyers fly straight
              lines (left plates y 29..30, right plates y 33..34) and the hero at y 32..38 on plate 460 alone meets neither: 0 instead of -40;
  (old legs 30-42 otherwise unchanged, to tokenU: the hound bite in room 28 sets the poison byte 2434(A5) = 10)
  out28       the old leg 43 (door $33 to room 30);
  drink491    drink the cure in room 30 (Return grid, icon 9): poison byte 10 -> 0, one of 4 doses used.  Drunk in room 28 with the hound in contact the dose
              is used and the byte is 10 again at once (re-bitten), so it is drunk after leaving;
  (old legs 44-45: toRoom14, tokenW)
  out14       GU:y<=50 (a stop at y lead 51 does not cross), HR through door $16 (y lead 50) into room 13 instead of GR:x>=79 + Z15:14 (the old leg's -10)
An I<oid>:<icon> word (first in a leg) opens that rucksack item's panel and picks the icon (item_icon(): explore.py's C/K lose the pulses here).
Each leg writes NN_<leg>.snap and prints room, bbox, health and the poison byte.  --from=<leg> resumes from OUTDIR's snapshot of the leg before."""
import sys, os
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import explore as EX
from explore import *
args = [a for a in sys.argv[1:] if not a.startswith('--')]; flags = dict(f[2:].split('=') for f in sys.argv[1:] if f.startswith('--'))
start, outdir = os.path.abspath(args[0]), os.path.abspath(args[1]); os.makedirs(outdir, exist_ok=True)

LEGS = [
    ('to20',      ['Z21', 'A20:95']),
    ('take491',   ['GD:y>=30', 'GR:x>=35', 'O2', 'S100000', 'A20:95']),
    ('back18b',   ['Z21', 'A18:95']),
    ('back16',    ['S600000', 'GU:y<=20', 'Z1c', 'N', 'A16:95']),
    ('back15',    ['Z1b:66', 'A15:95']),
    ('back14',    ['GR:x>=32', 'Z1f:15', 'A14:95']),
    ('scroll570a', ['GD:y>=37', 'GR:x>=36', 'A14:95']),
    ('scroll570b', ['O2', 'S100000', 'A14:95']),
    ('back13',    ['GL:x<=14', 'S300000', 'GU:y<=17', 'Z15:15', 'A13:95']),
    ('back3',     ['Z12:14', 'A3:95']),
    ('back2',     ['Z04', 'A2:95']),
    ('back1',     ['Z02', 'A1:95']),
    ('sleep',     ['I570:d', 'F', 'A1:95']),
    ('to89',      ['Z0f:23', 'A89:95']),
    ('tokenF_a',  ['GU:y<=36', 'GR:x>=37', 'O2', 'A89:95']),
    ('tokenF_b',  ['GL:x<=14', 'A89:95']),
    ('applyF',    ['I223:c', 'S300000', 'B206', 'A89:95']),
    ('to1',       ['HD', 'A1:95']),
    ('to2',       ['Z02:23', 'A2:95']),
    ('to30',      ['Z38', 'A30:95']),
    ('to28',      ['Z2f:11', 'A28:95']),
    ('tokenU',    ['GR:x>=23', 'GD:y>=48', 'O2', 'S100000', 'A28:95']),
    ('out28',     ['S2500000', 'Z33:42:60000', 'A30:95']),
    ('drink491',  ['I491:9', 'S200000', 'N', 'A30:95']),
    ('toRoom14',  ['Z38:21', 'A2:95', 'Z04', 'A3:95', 'Z12:14', 'A13:95', 'Z15:14', 'N', 'A14:95']),
    ('tokenW',    ['GD:y>=50', 'GL:x<=58', 'O2', 'S200000', 'N', 'A14:95']),
    ('out14',     ['GU:y<=50', 'HR', 'N', 'A13:95']),
]

def item_icon(inp, out, oid, icon, ks=range(1, 9)):
    """Return grid, k RIGHT pulses, FIRE (the item's panel), then icon `icon`.  k is searched on fresh loads of `inp` (so the kept run has the same reload as the
    trial): the first k whose panel holds `oid` and answers the joystick.  With 4 items in the rucksack a panel opened with k = 0 ignored every pulse
    (12 of 12 lost, from 12_back1 of this route), so k = 0 is not tried; the Return grid is four cells wide and RIGHT pulses cycle its first row only (k = 4 gives cell 3, then cell 0 again), so an item in
    cell 4 or later needs a DOWN (route_pocket.py's SEQS: `RD` is cell 4, `RDR` cell 5)."""
    from drv import cur_icon
    for k in ks:
        r = Repl(inp); t = Tally(r); tap(r, t, 0x1c)
        for _ in range(k): pulse(r, t, RIGHT)
        t.joy(FIRE); t.run(40000); t.joy(0); t.run(90000)
        if r.w(A5 + 1236) == oid:
            try:
                pick_icon_id(r, t, icon); t.run(100000)
                print('   item %d icon %d via k=%d, sel %s' % (oid, icon, k, r.a5(1262, 2).hex()), flush=True); r.snap(out); r.close(); return k
            except AssertionError: pass
        r.close()
    raise AssertionError(('item panel', oid, icon))

HAVE = {'take491': [491], 'scroll570b': [570], 'tokenF_a': [223], 'tokenU': [338], 'tokenW': [224]}

def check(name, out):
    """after each leg: the rucksack, VAR 9 (tokens applied), 491's dose byte and XP; asserts the items each leg takes and token F's application"""
    r = Repl(out); ruck = ruck_ids_data(r); v9 = r.b(A5 + 2282 + 9); b = live_body(r, 491); doses = r.b(b + 2) if b else None; xp = r.l(A5 + 1192); r.close()
    for o in HAVE.get(name, []): assert o in ruck, (name, o, ruck)
    if name == 'applyF': assert v9 == 1 and 223 not in ruck, (name, v9, ruck)
    return 'ruck %s var9 %d 491doses %s xp %d' % (ruck, v9, doses, xp)

names = [l[0] for l in LEGS]; i0 = names.index(flags['from']) if 'from' in flags else 0
cur = start if i0 == 0 else os.path.join(outdir, '%02d_%s.snap' % (i0, names[i0 - 1]))
for n, (name, cmds) in enumerate(LEGS[i0:], i0 + 1):
    out = os.path.join(outdir, '%02d_%s.snap' % (n, name))
    print('== leg %d %s: %s' % (n, name, ' '.join(cmds)), flush=True)
    if cmds[0][0] == 'I':          # I<oid>:<icon hex>: item_icon() first, then the rest of the leg through explore.py
        oid, ic = cmds[0][1:].split(':'); pre = out + '.pre.snap'; item_icon(cur, pre, int(oid), int(ic, 16)); cur, cmds = pre, cmds[1:]
    room, p, h, ps = EX.run(cur, out, cmds, tmp=os.path.join(outdir, '_scratch_%s' % name))
    print('   -> room %d pos %s health %d poison %d %s' % (room, p, h, ps, check(name, out)), flush=True)
    cur = out
    if flags.get('upto') == name: break
print('end room %d health %d poison %d' % (room, h, ps), flush=True)
