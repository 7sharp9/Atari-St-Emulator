"""print ss.asm lines around an address: asm_ctx.py <hexaddr> [before_bytes] [after_bytes]"""
import sys, os, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
a = int(sys.argv[1], 16); b = int(sys.argv[2]) if len(sys.argv) > 2 else 40; f = int(sys.argv[3]) if len(sys.argv) > 3 else 8
for l in open(os.path.join(sscfg.WORK, 'ss.asm')):
    m = re.match(r'\s+\$([0-9a-f]+):', l)
    if m and a - b <= int(m.group(1), 16) <= a + f: print(l.rstrip())
