"""drive_pre.py T [T...]: from ss_attract.snap drive the real game (injected IKBD input only) to a race on track T and
snapshot at the ENTRY of $be40 (race-start initialiser, before the track maps are rendered) -> snap/pre_T.snap.
Same input sequence as reversing/supersprint/py/tracks/drive_track.py --pre."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from uc import *

def drive(T):
    r = Repl2(sscfg.SNAP_ATTRACT)
    r.cmd('kbd fe 80'); r.cmd('s 400000'); r.cmd('kbd fe 00'); r.cmd('s 700000')
    o, reg = r.cmd2('bpc 19646 1 400000')
    a6 = reg['A6']; dial = int.from_bytes(r.mem(a6-4, 2), 'big'); tries = 0
    while dial != 2 * T and tries < 40:
        r.cmd('kbd fe 08'); r.cmd('s 60000'); r.cmd('kbd fe 00'); r.cmd('s 150000'); tries += 1
        dial = int.from_bytes(r.mem(a6-4, 2), 'big')
    assert dial >> 1 == T, (dial, T)
    r.cmd('kbd fe 80'); r.cmd('s 60000'); r.cmd('kbd fe 00'); r.cmd('s 1500000')
    r.cmd('kbd 2a'); r.cmd('s 300000'); r.cmd('kbd aa'); r.cmd('s 300000')
    r.cmd('kbd fe 80'); r.cmd('s 300000'); r.cmd('kbd fe 00')
    stop = 'be40'
    o, reg = r.cmd2('bpc %s 1 12000000' % stop)
    for attempt in range(60):
        if reg['PC'] == int(stop, 16): break
        r.cmd('kbd 2a'); r.cmd('s 100000'); r.cmd('kbd aa'); r.cmd('s 100000')
        r.cmd('kbd fe 80'); r.cmd('s 100000'); r.cmd('kbd fe 00')
        o, reg = r.cmd2('bpc %s 1 %d' % (stop, 400000 if attempt < 59 else 20000000))
    assert reg['PC'] == int(stop, 16), hex(reg['PC'])
    p = os.path.join(SNAP, 'pre_%d.snap' % T); r.cmd('snap ' + p)
    print('snapshot', p); r.close()

if __name__ == '__main__':
    for t in sys.argv[1:]: drive(int(t))
