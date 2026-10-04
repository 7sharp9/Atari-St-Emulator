"""frame_census.py <evt> [anchor=aad8] : per-frame call census.  Counts, for every call target, the number of
calls whose caller pc is inside COMMAND.PRG ($c470..$1f274) or the trap-3 dispatcher ($a652), divided by the number
of iterations (= calls of the anchor = trap#3 service 1, the page flip).  Prints `target  calls  per_frame`."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from evt_stats import load
from collections import Counter
start, recs = load(sys.argv[1]); anchor = int(sys.argv[2], 16) if len(sys.argv) > 2 else 0xaad8
c = Counter(); n = 0
for sc, pc, tgt, op, kind, fl in recs:
    if kind == 3:
        if tgt == anchor: n += 1
        if 0xc470 <= pc < 0x1f274 or pc == 0xa652: c[tgt] += 1
print(f"iterations (anchor ${anchor:x} calls): {n}")
for t, k in sorted(c.items()): print(f"${t:06x}\t{k}\t{k/max(n,1):.2f}")
