"""Tally who asks for which sound: runs a snapshot with `watch 17848 4` (the game's pending-sound
cell, long at $17848; every writer is a `move.l #n,$17848` or $f526 `move.l D0,$17848`) and
counts (writer PC, id) pairs.  Also reports how many requests were overwritten inside a frame
(the frame driver $c956/$cc62 consumes one request per frame, last write wins) and the ids that
the driver actually handed to $105e8 (writes of 0 from $c96a/$cc76 clear the cell after use).

Usage: tally_requests.py <snap> <steps> [--pre file] [--tag t]
"""
import argparse
import collections
import re

from btsnd_common import OUT
from verify_psg import run_repl

W = re.compile(r"WATCH: step=(\d+) pc=\$([0-9a-f]+) WriteWord \$0001784([89a]) <- \$([0-9a-f]+)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("snap")
    ap.add_argument("steps", type=int)
    ap.add_argument("--pre", default=None)
    ap.add_argument("--tag", default="tally")
    a = ap.parse_args()
    pre = open(a.pre).read() if a.pre else ""
    out, err = run_repl(a.snap, pre + "watch 17848 4\ns %d\nq\n" % a.steps, a.tag)
    ev = [(int(m.group(1)), int(m.group(2), 16), m.group(3), int(m.group(4), 16)) for m in W.finditer(err)]
    writes = collections.Counter()
    seq = []
    for step, pc, off, val in ev:
        if off == "a" and pc not in (0xc96a, 0xcc76):
            writes[(pc, val)] += 1
            seq.append((step, pc, val))
    consumed = sum(1 for e in ev if e[2] == "a" and e[1] in (0xc96a, 0xcc76))
    for (pc, val), n in sorted(writes.items()):
        print("writer $%06x requests id %d: %d times" % (pc, val, n))
    print("requests %d, handed to $105e8 (cell cleared by $c96a/$cc76) %d" % (len(seq), consumed))


if __name__ == "__main__":
    main()
