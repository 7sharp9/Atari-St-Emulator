"""Gate: the model's cell list against the game's list at $18f02, per captured pose.
usage: gate_scan.py [--break]   (reads scratchpad/midwinter/scan/snaps/*.snap written by cap_scan.sh)"""
import sys, os, glob
from common import DATA
import lists, scan_model as M
brk = '--break' in sys.argv
kw = {'width': [0, 1, 2, 3, 4, 5, 4, 3]} if brk else {}     # control: $17140 last entry 2 -> 3
snaps = sorted(glob.glob(os.path.join(DATA, 'snaps', 'h*.snap')),
               key=lambda p: (int(os.path.basename(p)[1:-5].split('_')[0]), p))
tot = ok = hok = 0
for s in snaps:
    h, cam, L = lists.cell_list(s)
    got = M.scan(h, **kw)
    m = sum(1 for a, b in zip(L, got) if a == b)
    tot += len(L); ok += m; hok += (L == got)
    print('heading %4d oct %d cam %s cells %3d model %3d positional match %3d/%3d %s' %
          (h, M.octant(h), cam, len(L), len(got), m, len(L), 'OK' if L == got else 'DIFF'))
print('%s cells in order %d/%d ; headings exact %d/%d' % ('BROKEN-MODEL CONTROL' if brk else 'scan gate', ok, tot, hok, len(snaps)))
