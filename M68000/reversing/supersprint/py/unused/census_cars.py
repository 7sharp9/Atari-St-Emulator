"""census_cars.py SNAP [HITS]: census of the car-sprite blitter $14a4a over a live race: at each entry (car index = word at 4(A7)) read the
drone flag -3914(A4)[car] and the heading -3706(A4)[car] and compute the B3 frame the blitter selects, (car*16 + heading + (0x40 if drone)),
as in $14a8a-$14ac8 (frame address = B3 + frame*256).  Prints the frames seen per (car, drone) and the unused rows of the 8 x 16 frame grid.
Race snapshot after $be40 (cars placed); input optional via KBD commands in env CARS_KBD ('kbd fe 80' = accelerate joystick-0 player)."""
import sys, os, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from uc import *

def census(snap, hits=1500, per_hit=200000, pre=None):
    r = Repl2(snapath(snap))
    for c in (pre or []): r.cmd(c)
    seen = collections.Counter(); human = set()
    for i in range(hits):
        o, regs = r.cmd2('bpc 14a4a 1 %d' % (30000000 if i == 0 else per_hit))
        if regs['PC'] != 0x14a4a: break
        car = int.from_bytes(r.mem(regs['A7'] + 4, 2), 'big')
        dr = int.from_bytes(r.mem(A4 - 3914 + 2 * car, 2), 'big')
        hd = int.from_bytes(r.mem(A4 - 3706 + 2 * car, 2), 'big', signed=True)
        seen[(car, dr, hd)] += 1
        if not dr: human.add(car)
    fl = [int.from_bytes(r.mem(A4 - 3914 + 2 * k, 2), 'big') for k in range(4)]
    r.close()
    return seen, human, fl

if __name__ == '__main__':
    snap = sys.argv[1]; hits = int(sys.argv[2]) if len(sys.argv) > 2 else 1500
    pre = [x for x in os.environ.get('CARS_KBD', '').split(';') if x]
    seen, human, fl = census(snap, hits, pre=pre)
    print('drone flags', fl, 'humans drawn as cars', sorted(human))
    rows = collections.defaultdict(set)
    for (car, dr, hd), n in seen.items():
        fr = car * 16 + hd + (0x40 if dr else 0)       # the blitter's frame index ($14aae-$14ac6): headings outside 0..15 spill into a neighbouring row
        rows[fr // 16].add(fr % 16)
        if not 0 <= hd <= 15: print('ODD heading', hd, 'car', car, 'drone', dr, 'x%d' % n, '-> frame', fr, '(row %d)' % (fr // 16))
    names = ['human blue', 'human red', 'human yellow', 'human green', 'drone blue', 'drone red', 'drone yellow', 'drone green']
    for row in range(8):
        print('B3 row %d (%s, frames %d..%d, file %x-%x): headings drawn %s' % (row, names[row], row * 16, row * 16 + 15,
              0x4d56 + row * 0x1000, 0x4d56 + (row + 1) * 0x1000, sorted(rows[row])))
