"""Drive the real game from ss_attract.snap to a race on track T (0-based) using only injected IKBD input:
   fe 80 leaves attract and opens the wheel; T joystick-right presses rotate the dial (dial = 2*T, track = dial>>1);
   a fire press ends the wheel; LShift + joystick fire join players; the countdown ends in $be40(T).
   Snapshots at the moment $15884/$1bc92 have built the background ($beb2, the call to $f386).
   usage: drive_track.py T [T ...]   -> snaps/race_T.snap"""
import sys; sys.path.insert(0,'.')
from tkcommon import *

def drive(T, verbose=True, stop_at='beb2', tag='race'):
    r = Repl2(sscfg.SNAP_ATTRACT)
    r.cmd('kbd fe 80'); r.cmd('s 400000'); r.cmd('kbd fe 00'); r.cmd('s 700000')
    o, reg = r.cmd2('bpc 19646 1 400000')
    a6 = reg['A6']; dial = int.from_bytes(r.mem(a6-4, 2), 'big'); tries = 0
    while dial != 2 * T and tries < 40:            # one right press advances the dial by 2 (one track)
        r.cmd('kbd fe 08'); r.cmd('s 60000'); r.cmd('kbd fe 00'); r.cmd('s 150000'); tries += 1
        dial = int.from_bytes(r.mem(a6-4, 2), 'big')
    if verbose: print('T=%d dial word at $%x = %d' % (T, a6-4, dial))
    assert dial >> 1 == T, (dial, T)
    r.cmd('kbd fe 80'); r.cmd('s 60000'); r.cmd('kbd fe 00'); r.cmd('s 1500000')
    # attempt 0: the exact sequence drive.repl uses (worked for tracks 1-5,7,8); fallback: keep pressing join until $be40 starts
    r.cmd('kbd 2a'); r.cmd('s 300000'); r.cmd('kbd aa'); r.cmd('s 300000')
    r.cmd('kbd fe 80'); r.cmd('s 300000'); r.cmd('kbd fe 00')
    o, reg = r.cmd2('bpc %s 1 12000000' % stop_at)
    for attempt in range(60):
        if reg['PC'] == int(stop_at, 16): break
        r.cmd('kbd 2a'); r.cmd('s 100000'); r.cmd('kbd aa'); r.cmd('s 100000')
        r.cmd('kbd fe 80'); r.cmd('s 100000'); r.cmd('kbd fe 00')
        o, reg = r.cmd2('bpc %s 1 400000' % stop_at if attempt < 59 else 'bpc %s 1 20000000' % stop_at)
    assert reg['PC'] == int(stop_at, 16), hex(reg['PC'])
    p = out('snaps', '%s_%d.snap' % (tag, T)); r.cmd('snap ' + p)
    if verbose: print('snapshot', p, 'A4=%x' % reg['A4'])
    r.close(); return p

if __name__ == '__main__':
    if sys.argv[1] == '--pre':                      # snapshot at $be40 entry (before $15884 builds anything)
        for t in sys.argv[2:]: drive(int(t), stop_at='be40', tag='pre')
    else:
        for t in sys.argv[1:]: drive(int(t))
