"""mouse_ghost.py - the IKBD ISR ($104b6) only understands $FE/$FF (joystick) packets; every other byte is stored as a scancode
make/break.  So a relative-mouse packet F8 dx dy (header ignored because (hdr&$7f) >= $76) deposits dx and dy as if they were keys.
Live proof from the attract snapshot: dx = $3b (scancode of F1) opens the options screen; dx = $2a (LShift) starts a session."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from probe import *
for tag, pkt in (('no packet', None), ('mouse F8 3b 00 (dx=59)', ['f8', '3b', '00']), ('mouse F8 2a 00 (dx=42)', ['f8', '2a', '00']), ('mouse F8 05 3b (dy=59)', ['f8', '05', '3b']), ('mouse F8 7f 7f (dx=dy=127: scancodes $7f >= $76 ignored)', ['f8', '7f', '7f'])):
    r = R(sscfg.SNAP_ATTRACT); r.cmd('s 500000')
    a = Acc(r, [0x18b54, 0x13a5e, 0x19164])
    if pkt: a.kbd(*pkt)
    a.run(1500000)
    print('%-58s' % tag, {hex(k): v for k, v in a.tot.items() if v}, 'F1 cell %02x LShift cell %02x' % (r.g8(-4743), r.g8(-4802 + 0x2a)))
    r.close()
