"""Print the linear listing between two addresses: lst.py <lo> <hi> (hex). Uses scratchpad/crudebuster/all_lin.txt and
annotates `lea N(PC)` targets and longword-table words as data."""
import os, sys
root = os.environ.get("M68000_ROOT") or os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
lo, hi = int(sys.argv[1], 16), int(sys.argv[2], 16)
for line in open(os.path.join(root, "scratchpad/crudebuster/all_lin.txt")):
    a = int(line[3:9], 16)
    if lo <= a < hi: print(line.rstrip())
