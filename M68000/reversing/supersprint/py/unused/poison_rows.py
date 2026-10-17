"""poison_rows.py SNAP 'SCRIPT' : A/B poison of the 8 car rows of B3 (4 KB each, file 0x4d56 + row*0x1000: rows 0..3 = human blue/red/yellow/green,
4..7 = drone blue/red/yellow/green) one at a time; prints the RAM bytes that differ outside the row at any '!dump' checkpoint."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from flow import *
if __name__ == '__main__':
    snap = snapath(sys.argv[1]); script = parse_script(sys.argv[2])
    rows = [[(0x4d56 + k * 0x1000, 0x4d56 + (k + 1) * 0x1000)] for k in range(8)]
    cpc, res = consumed(snap, script, rows, procs=int(os.environ.get('SCAN_PROCS', 3)))
    for k, (v, tot, ds, pc) in enumerate(res):
        print('B3 row %d %s: diff %d' % (k, ['human blue', 'human red', 'human yellow', 'human green', 'drone blue', 'drone red', 'drone yellow', 'drone green'][k], tot), flush=True)
