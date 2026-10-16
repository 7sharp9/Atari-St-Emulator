"""check_pigeon.py <dir>: the rows of gate_pigeon.sh, read from run.py's per-chunk logs (last line = end state)."""
import re, sys
from pathlib import Path
W = Path(sys.argv[1])
def rows(n):
    out = []
    for l in (W / f'{n}.log').read_text().splitlines():
        m = re.match(r'(\d+) (?:tgt \((\d+), (\d+)\) )?pend (\d+) state (\d+) .*?pos \((\d+), (\d+)\).*pigs (\[.*\])', l)
        if m: out.append(dict(step=int(m[1]), tgt=(int(m[2]), int(m[3])) if m[2] else None, pend=int(m[4]),
                              state=int(m[5]), pos=(int(m[6]), int(m[7])), pigs=m[8]))
    return out
cell = lambda r: (r['pos'][0] >> 8, r['pos'][1] >> 8)
ok = 0; checks = [
 ('s1: one order, camps at A (32,60)', lambda: cell(rows('s1')[-1]) == (32, 60) and rows('s1')[-1]['state'] == 6),
 ('s3: B alone, camps at B (26,60)', lambda: cell(rows('s3')[-1]) == (26, 60) and rows('s3')[-1]['state'] == 6),
 ('s2: A then B in flight together: both delivered, the later wins, camps at B', lambda: cell(rows('s2')[-1]) == (26, 60) and rows('s2')[-1]['pigs'] == '[]'),
 ('s4: A twice: camps at A like s1', lambda: cell(rows('s4')[-1]) == (32, 60)),
 ('ctl: dead sender: never delivered, pending stays 4, lead does not move', lambda: rows('ctl')[-1]['pend'] == 4 and rows('ctl')[-1]['pos'] == rows('ctl')[0]['pos']),
 ('alive: sender owner revived: delivered ($4220 clears pending), walks and camps', lambda: rows('alive')[-1]['pend'] == 0 and rows('alive')[-1]['state'] == 6 and rows('alive')[-1]['pos'] != rows('alive')[0]['pos']),
 ('snd0: sender word 0: runs at once (target (36,62) within 1M), pending untouched', lambda: [r for r in rows('snd0') if r['step'] <= 1_000_000 and r['tgt'] == (36, 62)] != [] and rows('snd0')[-1]['pend'] == 4),
]
for name, f in checks:
    try: r = f()
    except Exception as e: r = False; name += f' [{e}]'
    ok += bool(r); print('PASS' if r else 'FAIL', name)
print(f'{ok}/{len(checks)}')
