#!/usr/bin/env python3
"""Print a range of the static listing: lst.py LO HI  (hex), reads $BT_WORK/bt_c470.asm."""
import os, sys, re
from btram import ROOT, WORK
lo, hi = int(sys.argv[1], 16), int(sys.argv[2], 16)
for line in open(os.path.join(WORK, "bt_c470.asm")):
    m = re.match(r"\s*\$([0-9a-f]+):", line)
    if m and lo <= int(m.group(1), 16) < hi:
        sys.stdout.write(line)
