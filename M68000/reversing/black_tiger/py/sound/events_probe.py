"""Probe every map-object kind 3..$21 for a sound request by rewriting item record 0 ($1fb60) in
play_start.snap to that kind at the hero's own (x,y)  (LABELLED POKE: `w 1fb60 <kind><x>` and
`w 1fb64 <y><old bytes 8..9>`), then running 150,000 steps with `watch 17848 4`.
A kind with no row requested nothing.  Chest ($a) also gets one key.
Output: $BT_WORK/agents/sound/events_probe.tsv
"""
import os
import collections

from btsnd_common import BT_WORK, OUT, Snap
from events_drive import drive

sp = os.path.join(BT_WORK, "play_start.snap")
s = Snap(sp)
hx, hy = s.w(0x1f014), s.w(0x1f016)
tail = s.w(0x1fb68)
rows = []
for kind in range(3, 0x22):
    pre = ["w 1fb60 %04x%04x" % (kind, hx), "w 1fb64 %04x%04x" % (hy, tail)]
    if kind == 0x0a:
        pre.append("w 1f004 0001%04x" % s.w(0x1f006))
    c = drive(sp, pre, 150000, "probe_k%02x" % kind)
    rows.append((kind, c))
    print("kind %02x: %s" % (kind, ", ".join("$%06x->id%d x%d" % (pc, v, n) for (pc, v), n in sorted(c.items())) or "no request"))
with open(os.path.join(OUT, "events_probe.tsv"), "w") as f:
    f.write("kind\twriter_pc\tid\tcount\n")
    for kind, c in rows:
        for (pc, v), n in sorted(c.items()):
            f.write("%02x\t%06x\t%d\t%d\n" % (kind, pc, v, n))
