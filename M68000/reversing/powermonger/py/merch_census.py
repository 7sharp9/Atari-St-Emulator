"""merch_census.py <snap>...: live men with mode $4e..$54 (byte 31): mode, prev mode (30), dwell (18, signed), 46 (dest lord offset),
home lord offset (settlement 34 -> $4f916+14), cell (20/22), the lord's cell; job (7&$f)."""
import os, sys, struct, collections
ROOT = os.environ.get('M68000_ROOT') or os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
from disassemble import ram_from_snap
W = lambda r, a: struct.unpack('>H', r[a:a+2])[0]
SW = lambda r, a: struct.unpack('>h', r[a:a+2])[0]
for p in sys.argv[1:]:
    r = ram_from_snap(p)
    c = collections.Counter(); eq = tot = 0; rows = []
    for i in range(512):
        a = 0x51b66 + 50*i
        if r[a+5] == 0 or r[a+5] > 127 or r[a+6] != 0 or r[a+31] not in (0x4e, 0x50, 0x52, 0x54): continue
        sa = 0x4f916 + W(r, a+34); home = W(r, sa+14)
        d46 = W(r, a+46); tot += 1; eq += d46 == home
        rows.append((i, r[a+31], r[a+30], SW(r, a+18), d46, home, r[a+7] & 0xf, r[a+33], r[a+44], r[a+20], r[a+22]>>6 & 0x3f, W(r, sa+12) & 0x3f, (W(r, sa+12)>>6) & 0x7f))
        c[(r[a+31], r[a+30])] += 1
    print(os.path.basename(p), 'merchant-mode men', tot, '46==home lord', eq, 'job', collections.Counter(x[6] for x in rows))
    print('  (mode, prevmode) counts', {('%02x/%02x' % k): v for k, v in sorted(c.items())})
    if os.environ.get('V'):
        for x in rows: print('  man %3d mode %02x prev %02x dwell %4d d46 %3d home %3d job %d b33 %02x b44 %02x cellx %d' % x[:10])
