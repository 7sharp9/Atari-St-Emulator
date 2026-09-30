"""build_snaps.py - make the extra anchor snapshots this agent needs (all under agents/secrets/snap/):
   opt.snap        options screen (attract + F1)
   pre_winner.snap ss_prep run until the winner's-circle routine $1a4ca is entered (before the F5 poll at $1ad40)
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from probe import *
SNAP = os.path.join(AGENT, 'snap')
os.makedirs(SNAP, exist_ok=True)
which = sys.argv[1:] or ['opt', 'pre_winner']
if 'opt' in which:
    r = R(sscfg.SNAP_ATTRACT)
    r.cmd('s 500000')
    press(r, ['3b'], 60000)
    r.cmd('s 1500000')
    out, _ = r.cmd('snap %s' % os.path.join(SNAP, 'opt.snap'))
    print('opt', out[:3])
    r.close()
if 'pre_winner' in which:
    r = R(sscfg.SNAP_RACE)
    out, regs = r.cmd('u 1a4ca 60000000')
    print('pre_winner', out[:4], hex(regs['PC']))
    out, regs = r.cmd('snap %s' % os.path.join(SNAP, 'pre_winner.snap'))
    r.close()
