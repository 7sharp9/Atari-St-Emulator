"""Kill drops: when an actor in state 4 finishes its animation ($e4a4..$e502) an item of kind byte[$1771c + type] is created at the actor
(timer bytes 6/7 = $09/$41, so the coin is a 'dropped' coin without the +50 score).  Same labelled poke as killscore_check
(actor of type T, state 4, anim $30, in slot 100 = $1f670, at the hero); compares the new item kind against the table, 18 types
(type 5 is never killed)."""
import os, re, sys
sys.path.insert(0, os.path.dirname(__file__))
import btlib as b
snap = os.path.join(b.WORK, "play_start.snap")
ram = b.ram_from_snap(snap)
HX, HY = b.rw(ram, 0x1f014), b.rw(ram, 0x1f016)
REC = 0x1f670
drops = [ram[0x1771c + t] for t in range(0x14)]
ok = n = 0
for t in range(1, 0x14):
    if t == 5: continue
    lines = ["w %x %02x043000" % (REC, t), "w %x %04x%04x" % (REC + 4, HX + 100, HY), "w %x 00000000" % (REC + 8), "w %x 00000000" % (REC + 12),
             "s 200000", "m 1fb60 1640"]
    out = b.repl(snap, lines).splitlines()
    hexl = [l for l in out if re.fullmatch(r"([0-9a-f]{2} ?)+", l.strip())]
    items = bytes.fromhex("".join(hexl).replace(" ", ""))
    new = [(items[i] << 8) | items[i + 1] for i in range(0, len(items), 10) if items[i:i + 8] != ram[0x1fb60 + i:0x1fb60 + i + 8] and (items[i] << 8 | items[i + 1])]
    exp = [drops[t]] if drops[t] else []
    good = new == exp
    ok += good; n += 1
    print("actor type %02x: dropped item kinds %s  table %s  %s" % (t, [hex(k) for k in new], [hex(k) for k in exp], "OK" if good else "DIFF"))
print("kill-drop table matches %d/%d" % (ok, n))
