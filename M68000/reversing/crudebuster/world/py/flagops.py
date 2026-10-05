"""flagops.py <hexaddr...>: every bit operation / byte write on the flag cell(s) in the linear listing, grouped by bit and kind."""
import re, sys, os
from collections import defaultdict
root = os.environ.get("M68000_ROOT") or os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
lines = open(os.path.join(root, "scratchpad/crudebuster/all_lin.txt")).read().split("\n")
for tgt in sys.argv[1:]:
    ops = defaultdict(list)
    pat = re.compile(r"\$%s\.l" % tgt)
    for l in lines:
        if not pat.search(l): continue
        m = re.match(r"\s+\$([0-9a-f]+):\s+(\w+)(?:\.\w)?\s+(.*)", l)
        if not m: continue
        ad, op, rest = m.groups()
        mm = re.match(r"#(\d+),", rest)
        if op in ("bset", "bclr", "btst", "bchg") and mm: ops[(op, int(mm.group(1)))].append(ad)
        else: ops[(op + "*", None)].append(ad + ":" + rest.split(",")[0][:14])
    print("== $%s" % tgt)
    for k in sorted(ops, key=lambda k: (k[1] if k[1] is not None else -1, k[0])):
        print("  %-7s %-4s %s" % (k[0], "" if k[1] is None else "bit%d" % k[1], " ".join(ops[k][:30]) + (" ..." if len(ops[k]) > 30 else "")))
