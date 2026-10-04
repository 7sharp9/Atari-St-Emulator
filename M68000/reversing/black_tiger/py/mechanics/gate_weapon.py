"""Gate: weapon damage at $00e930 (hero melee/attack box vs one actor record, A3).  Model: hp -= 2*weaponLevel+1 ($1f00a);
if the byte result is negative: hp := 0, state := 4 (dying) unless already 4.  Labelled pokes: actor record at $1f670
(type 3, x = hero x + 16, y = hero y), $1781e = 4 (reach in 16px units), $1eeb4 = actor y - 4, facing $1f013 = 0 (right), D4 = $10."""
import os, re, sys
sys.path.insert(0, os.path.dirname(__file__))
import btlib as b
snap = os.path.join(b.WORK, "play_start.snap")
ram = b.ram_from_snap(snap)
HX, HY = b.rw(ram, 0x1f014), b.rw(ram, 0x1f016)
REC = 0x1f670
lines = ["w 1781e 00040000", "w 1f010 ff000000"]
cases = []
for lvl in range(5):
    for hp in (1, 2, 9, 20, 100):
        cases.append((lvl, hp))
        lines += ["w 1f00a %04x%s" % (lvl, ram[0x1f00c:0x1f00e].hex()), "w %x 03000000" % REC, "w %x %04x%04x" % (REC + 4, HX + 16, HY),
                  "w %x %02x000000" % (REC + 8, hp), "w 1eeb4 %04x%s" % (HY - 4, ram[0x1eeb6:0x1eeb8].hex()), "callcap e930 100000 A3=%x D4=10" % REC]
out = b.repl(snap, lines)
blocks = re.split(r"(?=^--- callcap)", out, flags=re.M)[1:]
ok = 0
for (lvl, hp), blk in zip(cases, blocks):
    m = re.search(r"^mem \$%06x \$([0-9a-f]+)->\$([0-9a-f]+)" % (REC + 8), blk, re.M)
    new = int(m.group(2), 16) if m else hp
    dmg = 2 * lvl + 1
    exp = hp - dmg
    exp = 0 if exp < 0 else exp
    ms = re.search(r"^mem \$%06x \$([0-9a-f]+)->\$([0-9a-f]+)" % (REC + 1), blk, re.M)
    state = int(ms.group(2), 16) if ms else 0
    exp_state = 4 if hp - dmg < 0 else 0          # state 4 = dying, only when the byte result is negative (zero is still alive)
    good = (new == exp and state == exp_state)
    ok += good
    if not good: print("lvl", lvl, "hp", hp, "got", new, state, "exp", exp, exp_state)
print("weapon damage 2*lvl+1 (+ dying state 4 only on a negative result): %d/%d match" % (ok, len(cases)))
