"""arena_map.py - parse the memory-layout allocator $fbca (chain of `move.l <prev>,D0 / add.l #size,D0 / move.l D0,<var>`) into the
pointer directory of the $4baf0-byte arena: each -N(A4) pointer, its offset in the arena and in SUPER.DAT (arena + $7d00 = SUPER.DAT base
-98(A4)), and the gap to the next pointer.  The pointers are the game's 'directory' of SUPER.DAT (a blob read once into the arena)."""
import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import reach
ins = reach.load()
code = [(a, t) for a, t in ins if 0xfbca <= a < 0xfd78]
val = {'-78(A4)': 0}       # arena offset of each variable
cur_src = None; add = None
pending = {}
for a, t in code:
    m = re.match(r'move.l (-?\d+\(A[46]\)),D0$', t)
    if m: cur_src = m.group(1); continue
    m = re.match(r'add.l #\$([0-9a-f]+),D0$', t)
    if m: add = int(m.group(1), 16); continue
    m = re.match(r'move.l D0,(-?\d+\(A[46]\))$', t)
    if m and cur_src is not None and add is not None:
        dst = m.group(1)
        if cur_src in val: val[dst] = val[cur_src] + add
        add = None; continue
    m = re.match(r'move.l (-?\d+\(A[46]\)),(-?\d+\(A4\))$', t)    # plain copies
    if m and m.group(1) in val: val[m.group(2)] = val[m.group(1)]
SUP = val['-98(A4)']
rows = sorted(val.items(), key=lambda kv: kv[1])
print('arena offset  SUPER.DAT offset   pointer      size-to-next')
for i, (k, v) in enumerate(rows):
    nxt = rows[i + 1][1] if i + 1 < len(rows) else None
    print('%7x  %10s  %-12s %s' % (v, ('%x' % (v - SUP)) if v >= SUP else '-', k, ('%d (0x%x)' % (nxt - v, nxt - v)) if nxt is not None and nxt > v else ''))
