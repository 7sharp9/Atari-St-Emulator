"""spawntable.py: compact table of stage-script spawn entries of kinds 1-3 (tag 2) from out/script_5f7e.txt (script_scan.py 5f7e): stage(190(A5)) area(191(A5)) group trigger (camera x / mode) entry x y sub name rank 2P-only"""
import os, re, sys
NAMES = {(1, 0): 'J', (1, 1): 'TWO.P', (2, 0): 'AXL', (2, 1): 'SLASH', (3, 0): 'ANDORE Jr.', (3, 1): 'ANDORE', (3, 2): 'G.ANDORE', (3, 3): 'U.ANDORE', (3, 4): 'F.ANDORE'}
trig = None; rows = []
for l in open(sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.environ.get('AI123_OUT', 'scratchpad/finalfight/p3/b/out'), 'script_5f7e.txt')):
    p = l.split()
    m = re.match(r's(\d+) a(\d+) (\w+) (TRIG|ENT|PAUSE)', l)
    if not m: continue
    s, a, addr, kind = int(m.group(1)), int(m.group(2)), m.group(3), m.group(4)
    if kind == 'TRIG':
        mode = re.search(r'mode(\d+)', l).group(1); x = re.search(r'x=(\w+)', l).group(1)
        trig = (s, a, addr, int(mode), x)
    elif kind == 'ENT':
        d = dict(t.split('=') for t in p[4:] if '=' in t)
        if d.get('tag') == '02' and d.get('kind') in ('01', '02', '03'):
            k = int(d['kind']); sub = int(d['sub'][:2], 16); b21 = int(d['sub'][2:], 16)
            rows.append((s, a, trig[2] if trig else '-', trig[3] if trig else -1, trig[4] if trig else '-', addr, d['x'], k, sub, b21, d['b14'], d['b15'], d['delay']))
print('stage area group@ mode trigger entry@ x kind sub name 21 b14(rank) b15(2P-only) delay')
for r in rows:
    nm = NAMES.get((r[7], r[8]), '?')
    rank = 'diff' if int(r[10], 16) >= 0x80 else str(int(r[10], 16))
    print('%d %d %s m%d %s %s %s k%d s%d %-10s b21=%d rank=%s 2P=%s delay=%d' % (r[0], r[1], r[2], r[3], r[4], r[5], r[6], r[7], r[8], nm, r[9], rank, 'yes' if int(r[11], 16) else 'no', int(r[12], 16)))
