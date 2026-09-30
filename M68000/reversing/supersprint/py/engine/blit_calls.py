"""List the calls to the rectangle blitters $1617a (copy w groups x h rows from a packed source) and $1671a/$166c0 (strip copy from a
sheet) with their immediate arguments, per function; shows how SUPER.DAT sections B0/B1/B2 are used.  usage: blit_calls.py <fn_hex>..."""
import sys, os, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
lines = open(os.path.join(sscfg.WORK, 'ss.asm')).read().split('\n')
funcs = sorted(int(m.group(1), 16) for l in open(os.path.join(sscfg.WORK, 'ss.c')) for m in [re.match(r'// ==== ([0-9a-f]{8}) ', l)] if m)
def rng(f):
    i = funcs.index(f); return f, (funcs[i + 1] if i + 1 < len(funcs) else f + 0x1000)
for fa in sys.argv[1:]:
    lo, hi = rng(int(fa, 16))
    print('=== $%x..$%x' % (lo, hi))
    stack = []
    for l in lines:
        m = re.match(r'\s+\$([0-9a-f]{6}): (.*)', l)
        if not m: continue
        a = int(m.group(1), 16)
        if not (lo <= a < hi): continue
        t = m.group(2)
        if re.match(r'(move\.[wl]|pea|clr\.[wl]) .*-\(A7\)', t) and 'jsr' not in t:
            stack.append(t)
        elif t.startswith('jsr'):
            mm = re.search(r'== \$([0-9a-f]+)', t)
            tgt = int(mm.group(1), 16) if mm else None
            mt = re.match(r'jsr (\d+)\(A5\)', t)
            if tgt in (0x1617a, 0x1671a, 0x166c0, 0x16766, 0x16282, 0x16496) or mt:
                print('  $%05x %s  args(top-first reversed order): %s' % (a, t, ' | '.join(reversed(stack[-8:]))))
            stack = []
