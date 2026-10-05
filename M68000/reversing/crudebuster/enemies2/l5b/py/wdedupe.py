"""Collapse the W lines of an objlog.txt (CB_TAP): print a line only when (addr, data, pc) differs from the last write to the same addr.
usage: wdedupe.py objlog.txt [f0 f1]"""
import sys
f0 = int(sys.argv[2]) if len(sys.argv) > 2 else 0
f1 = int(sys.argv[3]) if len(sys.argv) > 3 else 10**9
last = {}
for line in open(sys.argv[1]):
    if not line.startswith("W "): continue
    _, f, a, d, m, pc = line.split()
    if not f0 <= int(f) <= f1: continue
    k = (d, pc)
    if last.get(a) != k:
        print(line.rstrip()); last[a] = k
