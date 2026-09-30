"""builder_when.py - when/where is the collision world built? From ss_select.snap (SELECT TRACK): LShift-join (kbd 2a / aa), then break at
$15884 (the track loader: clear planes, compose art, walls+fill, colour classes, scenery, plane 0, surface map) and print the call chain and
the step distance to the first $df18 (first race frame)."""
import sys, os, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pl import *
e = Emu(sscfg.SNAP_SELECT)
e.cmd('kbd 2a'); e.cmd('s 300000'); e.cmd('kbd aa')
out, regs = e.cmd('bpc 15884 1 12000000')
print('first hit of $15884:', {k: hex(v) for k, v in regs.items() if k in ('PC', 'A7')}, [l.strip() for l in out if 'hit' in l or 'gave' in l][:2])
bt, _ = e.cmd('bt 8')
print('\n'.join(l for l in bt if l.strip()))
out, _ = e.cmd('m %x 10' % (regs['A7']))
print('args at SP:', [l for l in out if l.strip()][:2])
# census of the stages after this point
out, _ = e.cmd('hits 3000000 1552c 152d2 14cd4 15182 154d2 15550 be40 df18')
print('\n'.join(l for l in out if l.strip()))
out, regs = e.cmd('bpc df18 1 12000000')
print('first df18 reached:', [l.strip() for l in out if 'gave' in l] or 'yes')
e.close()
