"""Targeted live checks for the sound requests that need a stimulus (all from play_start.snap
or agents/systems/lvl4.snap; every poke labelled):
 1. urn burst -> id 1:  hero moved beside the level-1 urn (kind 1 at (840,160); `w 1f014 <x><y>`),
    fire held (`kbd ff 80`).  Control: hero 16 px lower (shots miss the urn).  `hits` on the
    urn-burst spawn $d5e4: 1 / 0.  Expected: id 1 requested once in the first, never in the control.
 2. time over -> id 2:  `w 1eedc ffff0000` (time word, mechanics' live time-out recipe).
 3. hero damage -> id 3:  level-4 snapshot, hero onto the first kind-$f item (`w 1f014 00b80200`),
    `watch 1eeb2` shows the invulnerability counter set at $e05c, 242 steps before the request at $e12e.
 4. chest ($a, one key: `w 1f004 0001<old $1f006>`) with 12 RNG seeds (`w 3195c`): id 8 requested for
    the seeds whose roll is 6 (the four-shot trap, $d3c4..$d40a), nothing otherwise.
"""
import os
import re

from btsnd_common import BT_WORK, OUT, Snap
from events_drive import drive
from verify_psg import run_repl

sp = os.path.join(BT_WORK, "play_start.snap")
s = Snap(sp)
fmt = lambda c: ", ".join("$%06x->id%d x%d" % (pc, v, n) for (pc, v), n in sorted(c.items())) or "none"

for label, dy in (("urn hit", 0), ("control (shots miss)", 16)):
    c = drive(sp, ["w 1f014 %04x%04x" % (864, 160 + dy), "kbd ff 80"], 300000, "misc_urn%d" % dy)
    out, err = run_repl(sp, "w 1f014 %04x%04x\nkbd ff 80\nhits 300000 d5e4\nq\n" % (864, 160 + dy), "misc_urnhits%d" % dy)
    hit = re.search(r"\$00d5e4\s+(\d+)", out)
    print("urn:", label, "| requests:", fmt(c), "| $d5e4 hits:", hit.group(1) if hit else "?")

print("time over:", fmt(drive(sp, ["w 1eedc ffff0000"], 600000, "misc_time")))

lv4 = os.path.join(BT_WORK, "agents", "systems", "lvl4.snap")
out, err = run_repl(lv4, "w 1f014 00b80200\nwatch 1eeb2 2\ns 150000\nq\n", "misc_dmg1")
out2, err2 = run_repl(lv4, "w 1f014 00b80200\nwatch 17848 4\ns 150000\nq\n", "misc_dmg2")
a = re.search(r"step=(\d+) pc=\$00e05c WriteWord \$0001eeb2 <- \$14", err)
b = re.search(r"step=(\d+) pc=\$00e12e WriteWord \$0001784a <- \$3", err2)
print("hero damage: $1eeb2<-$14 at step %s, id 3 at step %s (delta %s)" % (
    a and a.group(1), b and b.group(1), a and b and int(b.group(1)) - int(a.group(1))))

hx, hy = s.w(0x1f014), s.w(0x1f016)
res = []
roll6 = []
for seed in range(12):
    pre = ["w 1fb60 000a%04x" % hx, "w 1fb64 %04x0000" % hy, "w 1f004 0001%04x" % s.w(0x1f006),
           "w 3195c %08x" % (0x1234567 + seed * 0x9e3779)]
    res.append(drive(sp, pre, 400000, "misc_chest%d" % seed))
    out, err = run_repl(sp, "\n".join(pre) + "\nhits 400000 d3cc\nq\n", "misc_chesthits%d" % seed)
    m = re.search(r"\$00d3cc\s+(\d+)", out)
    roll6.append(bool(m and int(m.group(1))))
ids8 = [i for i, c in enumerate(res) if (0xf526, 8) in c]
print("chest seeds with id 8: %d/12 %s; seeds reaching the roll==6 branch $d3cc: %s; equal: %s" % (
    len(ids8), ids8, [i for i, r in enumerate(roll6) if r], ids8 == [i for i, r in enumerate(roll6) if r]))
