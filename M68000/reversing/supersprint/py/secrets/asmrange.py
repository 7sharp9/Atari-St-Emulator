"""asmrange.py LO HI  - print ss.asm lines with LO <= addr < HI (hex)"""
import os, re, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import sscfg
lo, hi = int(sys.argv[1], 16), int(sys.argv[2], 16)
for l in open(os.path.join(sscfg.WORK, 'ss.asm')):
    m = re.match(r'^\s+\$([0-9a-f]+):', l)
    if m and lo <= int(m.group(1), 16) < hi:
        sys.stdout.write(l)
