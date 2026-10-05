"""Print the lines of the linear listing scratchpad/crudebuster/all_lin.txt in [lo, hi) (hex).  usage: lst.py lo hi"""
import os, sys, re
ROOT = os.environ.get("M68000_ROOT") or os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
lo, hi = int(sys.argv[1], 16), int(sys.argv[2], 16)
for l in open(os.path.join(ROOT, "scratchpad/crudebuster/all_lin.txt")):
    m = re.match(r"\s+\$([0-9a-f]+):", l)
    if m and lo <= int(m.group(1), 16) < hi: sys.stdout.write(l)
