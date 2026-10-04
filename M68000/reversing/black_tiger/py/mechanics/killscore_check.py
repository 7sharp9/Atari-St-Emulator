"""Live check of the kill-score table $1775c (word per actor type, read at $e496..$e4a4).
Poke an actor record of type T in state 4 (dying) with an out-of-range animation index at the hero's position
(labelled poke: slot 100 of the $1f030 table = $1f670), run 3 ticks, report the score delta vs a control run."""
import os, re, sys
sys.path.insert(0, os.path.dirname(__file__))
import btlib as b
snap = os.path.join(b.WORK, "play_start.snap")
ram = b.ram_from_snap(snap)
HX, HY = b.rw(ram, 0x1f014), b.rw(ram, 0x1f016)
REC = 0x1f670
table = [b.rw(ram, 0x1775c + 2 * t) for t in range(0x14)]
def run(t):
    lines = []
    if t is not None:
        lines += ["w %x %02x043000" % (REC, t), "w %x %04x%04x" % (REC + 4, HX, HY), "w %x 00000000" % (REC + 8), "w %x 00000000" % (REC + 12)]
    lines += ["s 200000", "m 1eebc 4", "m %x 2" % REC]
    out = b.repl(snap, lines).splitlines()
    hexl = [l for l in out if re.fullmatch(r"([0-9a-f]{2} ?)+", l.strip())]
    return int(hexl[-2].replace(" ", ""), 16), hexl[-1]
ctl, _ = run(None)
ok = 0
for t in range(1, 0x14):
    sc, rec = run(t)
    good = (sc - ctl) == table[t]
    ok += good
    print("actor type %02x: score delta %5d  table[%d]=%5d  %s  (record after: %s)" % (t, sc - ctl, t, table[t], "MATCH" if good else "differs", rec))
print("matches %d/19" % ok)
