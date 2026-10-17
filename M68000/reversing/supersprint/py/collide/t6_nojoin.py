"""t6_nojoin.py [T=5] - drive attract -> SELECT TRACK dial to track T (0-based) -> fire, then join nobody; report whether the race initialiser $be40 and the
race loop $df18 are reached within the step budget, else the stopping PC.  (Track 6 once ended in a garbage PC: an emulator MFP bug, fixed in 6a1d544.)"""
import sys, os
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.environ.get('M68000_ROOT') or os.path.normpath(os.path.join(HERE, '..', '..', '..', '..'))
TK = os.path.join(ROOT, 'reversing', 'supersprint', 'py', 'tracks'); sys.path.insert(0, TK); os.chdir(TK)
from tkcommon import *
T = int(sys.argv[1]) if len(sys.argv) > 1 else 5
r = Repl2(sscfg.SNAP_ATTRACT)
r.cmd('kbd fe 80'); r.cmd('s 400000'); r.cmd('kbd fe 00'); r.cmd('s 700000')
o, reg = r.cmd2('bpc 19646 1 400000'); a6 = reg['A6']
for _ in range(40):
    if int.from_bytes(r.mem(a6 - 4, 2), 'big') == 2 * T: break
    r.cmd('kbd fe 08'); r.cmd('s 60000'); r.cmd('kbd fe 00'); r.cmd('s 150000')
r.cmd('kbd fe 80'); r.cmd('s 60000'); r.cmd('kbd fe 00'); r.cmd('s 1500000')
for tgt, budget in (('be40', 60000000), ('df18', 20000000)):
    o, reg = r.cmd2('bpc %s 1 %d' % (tgt, budget))
    print('T%d no join: bpc $%s -> PC=%08x' % (T + 1, tgt, reg['PC']), 'reached' if reg['PC'] & 0xffffff == int(tgt, 16) else 'NOT reached')
    if reg['PC'] & 0xffffff != int(tgt, 16): break
r.close()
