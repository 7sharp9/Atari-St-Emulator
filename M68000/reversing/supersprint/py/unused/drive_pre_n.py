"""drive_pre_n.py TRACK JOINERS TAG: like drive_pre.py but with a chosen set of human players.  JOINERS is a comma list from
{k (LShift = blue, channel 0), j0 (joystick 0 fire = red), j1 (joystick 1 fire = yellow)}; the first joiner is the one that
leaves the wheel screen (fe 80 as in drive_pre).  Snapshot at the entry of $be40 -> snap/<TAG>.snap.
    python3 drive_pre_n.py 0 k,j0,j1 pre3_t0"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from uc import *
KEY = {'k': ('kbd 2a', 'kbd aa'), 'j0': ('kbd fe 80', 'kbd fe 00'), 'j1': ('kbd ff 80', 'kbd ff 00')}

def drive(T, joiners, tag):
    r = Repl2(sscfg.SNAP_ATTRACT)
    r.cmd('kbd fe 80'); r.cmd('s 400000'); r.cmd('kbd fe 00'); r.cmd('s 700000')
    o, reg = r.cmd2('bpc 19646 1 400000')
    a6 = reg['A6']; dial = int.from_bytes(r.mem(a6 - 4, 2), 'big'); tries = 0
    while dial != 2 * T and tries < 40:
        r.cmd('kbd fe 08'); r.cmd('s 60000'); r.cmd('kbd fe 00'); r.cmd('s 150000'); tries += 1
        dial = int.from_bytes(r.mem(a6 - 4, 2), 'big')
    assert dial >> 1 == T, (dial, T)
    r.cmd('kbd fe 80'); r.cmd('s 60000'); r.cmd('kbd fe 00'); r.cmd('s 1500000')
    for j in joiners:
        mk, br = KEY[j]
        r.cmd(mk); r.cmd('s 300000'); r.cmd(br); r.cmd('s 300000')
    o, reg = r.cmd2('bpc be40 1 20000000')
    assert reg['PC'] == 0xbe40, hex(reg['PC'])
    p = os.path.join(SNAP, tag + '.snap'); r.cmd('snap ' + p)
    # how many humans: drone flags -3914(A4)[0..3]
    fl = [int.from_bytes(r.mem(A4 - 3914 + 2 * i, 2), 'big') for i in range(4)]
    print('snapshot', p, 'drone flags', fl); r.close()

if __name__ == '__main__':
    drive(int(sys.argv[1]), sys.argv[2].split(','), sys.argv[3])
