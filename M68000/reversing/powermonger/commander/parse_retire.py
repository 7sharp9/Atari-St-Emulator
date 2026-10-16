"""parse_retire.py [arm...]: per arm, per 10M chunk: the non-zero hits (count, first step within the chunk) and the
RAM dump after it ($57fce ratio, $3f2a0[0..3], $2df6e menu mode, $51690 side 1 group 0 owner word, side 1's slot, PC)."""
import re, sys
from pathlib import Path
import os
ROOT = next(d for d in Path(__file__).resolve().parents if (d / 'tools' / 'rdis.py').exists())
W = ROOT / os.environ.get('CMD_WORK', 'scratchpad/cmd1') / 'retire'
for arm in sys.argv[1:] or 'ctl post postwin dissolve post0 postwin0'.split():
    t = (W / f'{arm}.out').read_text().split('\n')
    print(f'=== {arm}')
    blk, mem, chunk = [], [], 0
    def flush():
        if mem: print(f'  [{chunk}] ratio={mem[0]} 3f2a0={mem[1]} 2df6e={mem[2]} 51690={mem[3]} slot={mem[4]} PC={pc}', ' '.join(blk))
    pc = None
    for l in t:
        if l.startswith('--- hits over'):
            flush(); blk, mem = [], []; chunk += 1
        m = re.match(r'\s+\$0*([0-9a-f]+)\s+(\d+)\s+first (-?\d+)', l)
        if m and int(m.group(2)): blk.append(f'{m.group(1)}x{m.group(2)}@{m.group(3)}')
        if re.fullmatch(r'[0-9a-f]{2}( [0-9a-f]{2})*', l.strip()): mem.append(l.strip().replace(' ', ''))
        m = re.match(r'PC: ([0-9a-f]+)', l)
        if m: pc = m.group(1)[-5:]
    flush()
