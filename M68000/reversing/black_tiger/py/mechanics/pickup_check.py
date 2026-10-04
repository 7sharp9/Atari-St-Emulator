"""Live check of the item-type dispatch at $cf20 (handlers via $ceec): poke one item of each type
at the hero's feet in a free $1fb60 slot of play_start.snap, run 3 game ticks, diff the HUD state against a
no-item control run from the same snapshot.  Labelled pokes: the item record (slot 100, $1ff48).
Usage: pickup_check.py [types...]  (default 3..0x22)"""
import os, re, sys
sys.path.insert(0, os.path.dirname(__file__))
import btlib as b
snap = os.path.join(b.WORK, "play_start.snap")
ram = b.ram_from_snap(snap)
HX, HY = b.rw(ram, 0x1f014), b.rw(ram, 0x1f016)
SLOT = 0x1ff48
FIELDS = [("zenny", 0x1f002, 2), ("keys", 0x1f004, 2), ("armour", 0x1f006, 2), ("potions", 0x1f008, 2), ("weapon", 0x1f00a, 2),
          ("lives", 0x1f00c, 2), ("vitality", 0x1f00e, 2), ("score", 0x1eebc, 4), ("snd", 0x17848, 4), ("t17824", 0x17824, 2),
          ("timer", 0x1eedc, 2), ("pos_x", 0x1f014, 2), ("pos_y", 0x1f016, 2), ("poison", 0x17820, 2), ("item_type", SLOT, 2),
          ("anchor_3f", 0x1eff2, 4)]
def run(t):
    lines = []
    if t is not None:
        lines += ["w %x %04x%04x" % (SLOT, t, HX), "w %x %04x0000" % (SLOT + 4, HY)]
    lines += ["s 200000"]
    for n, a, w in FIELDS: lines.append("m %x %d" % (a, w))
    out = b.repl(snap, lines).splitlines()
    hexl = [l for l in out if re.fullmatch(r"([0-9a-f]{2} ?)+", l.strip())]
    vals = {}
    for (n, a, w), l in zip(FIELDS, hexl[-len(FIELDS):]):
        vals[n] = int(l.replace(" ", ""), 16)
    return vals
types = [int(x, 0) for x in sys.argv[1:]] or list(range(3, 0x23))
ctl = run(None)
print("control (no item):", {k: hex(v) for k, v in ctl.items() if k in ("zenny","score","timer","snd")})
for t in types:
    r = run(t)
    d = {k: (r[k] - ctl[k]) for k in r if k not in ("item_type",) and r[k] != ctl[k]}
    print("type %02x: item word after=%04x  diffs vs control: %s" % (t, r["item_type"], {k: (hex(v) if k in ("snd","anchor_3f") else v) for k, v in d.items()}))
