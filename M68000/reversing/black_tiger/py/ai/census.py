#!/usr/bin/env python3
"""Per-level spawn census from the level files `0`..`7` via the gated reference btai.cd58
(writes $BT_WORK/agents/ai/spawn_census.txt).  Actor type -> count (records, so type $d counts 2 per
map code and $f counts 3), map-object kinds, markers and the boss record of $17226."""
import os
from collections import Counter
from btram import *
import btai

base = load("play_start.snap")
lines = []
for n in "01234567":
    d = open(os.path.join(WORK, "files", n), "rb").read()
    ram = bytearray(base)
    ram[0x201C8:0x201C8 + len(d)] = d
    for k in range(0x1F020, 0x1F020 + 16 * 179): ram[k] = 0
    m = btai.Mem(ram)
    btai.cd58(m)
    act = Counter(m.r[0x1F030 + 16 * i] for i in range(179) if m.r[0x1F030 + 16 * i])
    obj = Counter(m.w(btai.MOBJ + 10 * i) for i in range(164) if m.w(btai.MOBJ + 10 * i))
    mk = {k: (m.w(a), m.w(a + 2)) for k, a in (("start", 0x1EFF2), ("pt2", 0x1EFF6), ("bossxy", 0x1EFFA))}
    b = m.r[0x17226 + 4 * int(n):0x17226 + 4 * int(n) + 3]
    lines.append("level file %s (%dx%d tiles): %d actor records, %d map objects" % (n, d[1], d[3], sum(act.values()), sum(obj.values())))
    lines.append("  actor type:count  " + " ".join("%d:%d" % kv for kv in sorted(act.items())))
    lines.append("  map object kind:count  " + " ".join("%d:%d" % kv for kv in sorted(obj.items())))
    lines.append("  markers (x,y) " + str(mk) + "  boss table $17226[%s] = count %d type %d textid %d" % (n, b[0], b[1], b[2]))
open(os.path.join(OUT, "spawn_census.txt"), "w").write("\n".join(lines) + "\n")
print("\n".join(lines))
