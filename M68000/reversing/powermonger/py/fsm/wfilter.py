#!/usr/bin/env python3
"""wfilter.py: stdin WATCH lines over the object array -> stdout only writes whose start byte is at record offset
0..7 (side byte 5, category 6) or 28..31 (owner link, prev mode 30, mode 31). A long at 28 or a word at 30 is kept.
Optional arguments add start offsets as lo-hi ranges: `wfilter.py 46-49` also keeps the link target word 48."""
import re, sys
extra = [tuple(map(int, a.split('-'))) for a in sys.argv[1:]]
R = re.compile(r'\$([0-9a-f]{8}) <- ')
for l in sys.stdin:
    m = R.search(l)
    if not m:
        continue
    off = (int(m.group(1), 16) - 0x51b66) % 50
    if off <= 7 or 28 <= off <= 31 or any(lo <= off <= hi for lo, hi in extra):
        sys.stdout.write(l)
