"""Live drive of the shop man (item kind $11) on level 1: poke money 5000 and the hero onto the shop man cell (1256,224)
(labelled pokes: $1f002 money, $1f014 x/y), run to the shop entry $f690, then buy by moving the cursor with joystick 1 and pressing fire.
Prints money / keys / armour / potions / weapon after each action and writes screenshots (img prefix = argv[1] or $BT_WORK/agents/mechanics/shop_live).
Expected (code model gate_shop): fire on item0 -100 and weapon 0->1; right+fire item1 -1000 and weapon 2; etc."""
import os, re, sys
sys.path.insert(0, os.path.dirname(__file__))
import btlib as b
snap = os.path.join(b.WORK, "play_start.snap")
pref = sys.argv[1] if len(sys.argv) > 1 else os.path.join(b.OUT, "shop_live")
def state_lines():
    return ["m 1f002 10"]
steps = [("enter", []), ("fire (item 0)", ["kbd ff 80", "s 100000", "kbd ff 00", "s 400000"]),
         ("right+fire (item 1)", ["kbd ff 08", "s 100000", "kbd ff 00", "s 200000", "kbd ff 80", "s 100000", "kbd ff 00", "s 400000"]),
         ("right+fire (item 2)", ["kbd ff 08", "s 100000", "kbd ff 00", "s 200000", "kbd ff 80", "s 100000", "kbd ff 00", "s 400000"]),
         ("right+fire (item 3, 9600: refused with 5000-...)", ["kbd ff 08", "s 100000", "kbd ff 00", "s 200000", "kbd ff 80", "s 100000", "kbd ff 00", "s 400000"])]
lines = ["w 1f002 13880000", "w 1f014 04e800e0", "bp f690 4000000", "s 1000000", "m 1f002 12", "snap %s/snaps/shop_live_0.snap" % b.OUT]
for k, (name, cmds) in enumerate(steps[1:], 1):
    lines += cmds + ["m 1f002 12", "snap %s/snaps/shop_live_%d.snap" % (b.OUT, k)]
out = b.repl(snap, lines)
rows = [l for l in out.splitlines() if re.fullmatch(r"([0-9a-f]{2} ?)+", l.strip())]
for (name, _), r in zip(steps, rows):
    v = [int(x, 16) for x in r.split()]
    w = lambda i: (v[i] << 8) | v[i + 1]
    print("%-45s money %5d keys %d armour %d potions %d weapon %d" % (name, w(0), w(2), w(4), w(6), w(8)))
