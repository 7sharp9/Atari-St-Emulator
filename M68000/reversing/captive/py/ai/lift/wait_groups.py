"""Let a state run with no input and sample the groups near a box: wait_groups.py <snap> <total_steps> <every> <x0,y0,x1,y1> [save_at:out.snap ...]
Prints, every <every> steps, each group whose cell lies in the box (index, x, y, flags +5)."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fight import groups, srv, w16  # noqa
s = srv(sys.argv[1]); tot, ev = int(sys.argv[2]), int(sys.argv[3]); x0, y0, x1, y1 = map(int, sys.argv[4].split(','))
saves = dict((int(a.split(':')[0]), a.split(':')[1]) for a in sys.argv[5:])
for t in range(ev, tot + 1, ev):
    s('step', n=ev)
    print(t, [(i, x, y, f'{f:02x}') for i, a, x, y, f, hp in groups(s) if x0 <= x <= x1 and y0 <= y <= y1], flush=True)
    if t in saves:
        s('save', path=os.path.abspath(saves[t]))
s.close()
