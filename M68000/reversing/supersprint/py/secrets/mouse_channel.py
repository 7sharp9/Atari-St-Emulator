"""mouse_channel.py - the options screen can never select channel 1 ('mouse'); force it by poking and show that the channel reads as 'no input'.
ss_prep.snap: red car (index 1) is the human on channel 2.  Case A: channel 2 + joystick fire -> car accelerates.  Case B: poke channel word to 1
('mouse') + joystick fire + mouse button packets (F9 00 00 / FA 00 00) -> car stays at speed 0."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from probe import *
for tag, ch, cmds in (('channel 2 (joystick 0) + fire', 2, ['kbd fe 80']), ('channel 1 (mouse) + joystick fire + right/left mouse buttons', 1, ['kbd fe 80', 'kbd f9 00 00', 'kbd fa 00 00'])):
    r = R(sscfg.SNAP_RACE)
    r.cmd('s 20000')
    yellow = r.g16(-4806)
    r.cmd('w %x %04x%04x' % (sscfg.A4 - 4808, ch, yellow))
    for c in cmds: r.cmd(c)
    r.cmd('s 1200000')
    print('%-60s red channel word=%d  red speed=%d  pos=(%d,%d)' % (tag, r.g16(-4808), r.g16(-3730 + 2), r.g16(-3690 + 2), r.g16(-3698 + 2)))
    r.close()
