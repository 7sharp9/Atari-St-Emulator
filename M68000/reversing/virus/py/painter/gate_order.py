"""gate_order.py <snap> <frames>   Interleave of tile rows and bucket lists in the painter loop ($243b6..$24478).
Stops at $26b78 (tile filler, one call per tile), $243ec (bucket draw after a tile row; D0 = row counter c, so the bucket
is c+1, skipped when >= $a) and $24436 (the last bucket, number 0) and $24478 (painter end), for <frames> frames from the
painter's entry, and prints the run-length sequence of one frame plus a check that every frame is
  12 tiles, then for rows 0..10: bucket c+1 (c = 10 - row), skipped for rows 0 and 1  ...  bucket 0, end.
Own stserver; no files written."""
import os, sys, struct, collections
d = os.path.dirname(os.path.abspath(__file__))
while not os.path.exists(os.path.join(d, 'tools', 'rdis.py')): d = os.path.dirname(d)
ROOT = d; sys.path.insert(0, os.path.join(ROOT, 'tools'))
from stclient import StServer
def pc_of(r):
    p = r['pc']; return int(p.lstrip('$'), 16) if isinstance(p, str) else p
snap, nfr = sys.argv[1], int(sys.argv[2])
s = StServer(ROOT); s('load', snapshot=os.path.join(ROOT, snap))
s('bp_set', addrs=[0x243b6, 0x26b78, 0x243ec, 0x24436, 0x24478])
seqs = []; cur = None; last = None
while len(seqs) < nfr:
    r = s('run', max_steps=3000000); pc = pc_of(r)
    if r['reason'] != 'breakpoint': print('stopped', r['reason']); break
    if pc == last and r['steps'] < 64: continue
    last = pc
    if pc == 0x243b6: cur = []
    elif cur is None: continue
    elif pc == 0x26b78: cur.append('T')
    elif pc == 0x243ec: cur.append('B%d' % ((s.reg('d0') & 0xffff) + 1))
    elif pc == 0x24436: cur.append('B0')
    elif pc == 0x24478: seqs.append(cur); cur = None
def rle(seq):
    out = []; 
    for x in seq:
        if out and out[-1][0] == x: out[-1][1] += 1
        else: out.append([x, 1])
    return ' '.join(f'{x}x{n}' if n > 1 else x for x, n in out)
print('frame 0:', rle(seqs[0]))
for q, n in collections.Counter(rle(q) for q in seqs).most_common(4): print(n, 'frames:', q)
print('distinct sequences over', len(seqs), 'frames:', collections.Counter(rle(q) for q in seqs).most_common(3).__len__(), '; all equal to frame 0:', sum(rle(q) == rle(seqs[0]) for q in seqs))
s.close()
