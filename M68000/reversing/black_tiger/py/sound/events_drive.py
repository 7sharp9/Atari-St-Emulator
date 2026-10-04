"""Which map-object kind (and which boss/shop/chest drive) requests which sound id, per level.

For every level snapshot (level index 0 = play_start.snap, 1..7 = agents/systems/lvl1..7.snap) and
every distinct item kind in that level's item table ($1fb60, 164 x 10 bytes: kind word, x, y, ...)
the hero is moved onto the first record of that kind (LABELLED POKE: `w 1f014 <x><y>`, the hero
record's x and y words are adjacent, one deliberate longword), `watch 17848 4` is armed and
150,000 steps are run.  Writers of the pending-sound cell are tallied as (writer PC, id).
Chest ($a) gets one key first (LABELLED POKE: word $1f004 := 1, with $1f006 rewritten unchanged).

Usage: events_drive.py [--levels 0,1,..] [--steps N] [--kinds hex,hex]
Output: $BT_WORK/agents/sound/events_by_kind.tsv  (level, kind, x, y, writer pc, id, count)
"""
import argparse
import collections
import os
import re

from btsnd_common import BT_WORK, OUT, Snap
from verify_psg import run_repl

W = re.compile(r"WATCH: step=(\d+) pc=\$([0-9a-f]+) WriteWord \$0001784a <- \$([0-9a-f]+)")


def snap_path(level):
    return os.path.join(BT_WORK, "play_start.snap" if level == 0 else "agents/systems/lvl%d.snap" % level)


def items(s):
    out = collections.OrderedDict()
    for i in range(164):
        a = 0x1fb60 + 10 * i
        k = s.w(a)
        if k == 0:
            continue
        out.setdefault(k & 0xff, (s.w(a + 2), s.w(a + 4)))
    return out


def drive(snap, pre, steps, tag):
    lines = pre + ["watch 17848 4", "s %d" % steps]
    out, err = run_repl(snap, "\n".join(lines) + "\nq\n", tag)
    c = collections.Counter()
    for m in W.finditer(err):
        pc, val = int(m.group(2), 16), int(m.group(3), 16)
        if pc in (0xc96a, 0xcc76) or val == 0:
            continue
        c[(pc, val)] += 1
    return c


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--levels", default="0,1,2,3,4,5,6,7")
    ap.add_argument("--steps", type=int, default=150000)
    ap.add_argument("--kinds", default=None)
    a = ap.parse_args()
    want = None if a.kinds is None else {int(x, 16) for x in a.kinds.split(",")}
    rows = []
    for lv in [int(x) for x in a.levels.split(",")]:
        sp = snap_path(lv)
        s = Snap(sp)
        for kind, (x, y) in items(s).items():
            if want is not None and kind not in want:
                continue
            pre = ["w 1f014 %04x%04x" % (x, y)]
            if kind == 0x0a:
                pre.append("w 1f004 0001%04x" % s.w(0x1f006))
            c = drive(sp, pre, a.steps, "ev_l%d_k%02x" % (lv, kind))
            rows.append((lv, kind, x, y, c))
            print("level %d kind %02x at (%d,%d): %s" % (lv, kind, x, y,
                  ", ".join("$%06x->id%d x%d" % (pc, v, n) for (pc, v), n in sorted(c.items())) or "no request"))
    with open(os.path.join(OUT, "events_by_kind.tsv"), "w") as f:
        f.write("level\tkind\tx\ty\twriter_pc\tid\tcount\n")
        for lv, kind, x, y, c in rows:
            if not c:
                f.write("%d\t%02x\t%d\t%d\t-\t-\t0\n" % (lv, kind, x, y))
            for (pc, v), n in sorted(c.items()):
                f.write("%d\t%02x\t%d\t%d\t%06x\t%d\t%d\n" % (lv, kind, x, y, pc, v, n))


if __name__ == "__main__":
    main()
