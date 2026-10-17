"""tables.py: list the C-initialised A4-relative tables set in $11b24..$11d44 (lea -N(A4),A1 followed by move.[wlb] #imm,(A1)+ runs):
offset, element size, count, values.  Cross-reference: number of `-N(A4)` mentions elsewhere in ss.asm (consumers)."""
import re, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from uc import *
asm = open(os.path.join(sscfg.WORK, 'ss.asm')).read().split('\n')
ins = []
for l in asm:
    m = re.match(r'\s+\$([0-9a-f]{6}): (.*)', l)
    if m: ins.append((int(m.group(1), 16), m.group(2)))
tabs = []
cur = None
for a, t in ins:
    if not (0x11b24 <= a < 0x11d50): continue
    m = re.match(r'lea (-?\d+)\(A4\),A([0-7])', t)
    if m: cur = [int(m.group(1)), int(m.group(2)), None, []]; tabs.append(cur); continue
    m = re.match(r'move\.([wlb]) #\$([0-9a-f]+),\(A(\d)\)\+', t)
    if m and cur and int(m.group(3)) == cur[1]:
        cur[2] = m.group(1); cur[3].append(int(m.group(2), 16))
for off, reg, sz, vals in tabs:
    if not vals: continue
    n = sum(1 for a, t in ins if re.search(r'(?<![\d-])%d\(A4\)' % off, t) and not (0x11b24 <= a < 0x11d50))
    print('%6d(A4) %s x%-3d  refs-outside-init %-3d %s' % (off, sz, len(vals), n, vals if len(vals) <= 24 else str(vals[:24]) + '...'))
