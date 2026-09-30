"""esc_prepare.py - ESC (scancode $01) on the PREPARE-TO-RACE screen.  $18626 reads the ESC cell (-4801(A4)) every frame of the
countdown loop of $18024 and clears the countdown word -4(A6) (initial $12c... decremented by 4/frame).  A/B from one snapshot:
steps until the race loop $df18 is first entered, with and without ESC held."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from probe import *
r = R(sscfg.SNAP_ATTRACT)
r.cmd('s 500000'); press(r, ['2a'], 60000); r.cmd('s 1500000'); press(r, ['2a'], 60000)
out, g = r.cmd('u 18626 60000000'); print('in prepare loop at', hex(g['PC']))
r.cmd('snap %s' % os.path.join(AGENT, 'snap', 'prep_kbd.snap'))
r.close()
def run(tag, esc):
    r = R(os.path.join(AGENT, 'snap', 'prep_kbd.snap'))
    if esc: r.cmd('kbd 01'); r.cmd('s 60000')
    a = Acc(r, [0x18626, 0xdf18])
    # count frames of the countdown loop until $df18
    out, g = r.cmd('u df18 60000000')
    m = [l for l in out if 'reached' in l]
    h, _ = hits(r, 0, [0]) if False else (None, None)
    print('%-22s %s' % (tag, m[0].strip() if m else out[:3]))
    r.close()
run('no ESC', False)
run('ESC held ($01 make)', True)
