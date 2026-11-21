"""SPACE on the title -> launch sequence: tap SPACE on g_title then snapshot every N steps and render each.
usage: screens_launch.py [N=1500000] [count=10] -> WORK/frontend/launch_t<k>.snap/.png"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fe_repl, sgcommon
n = int(sys.argv[1]) if len(sys.argv) > 1 else 1500000
cnt = int(sys.argv[2]) if len(sys.argv) > 2 else 10
out = sgcommon.work('frontend')
cmds = fe_repl.key('39', 200000)
for k in range(cnt):
    cmds += ['s %d' % n, 'snap %s' % os.path.join(out, 'launch_t%d.snap' % k)]
o = fe_repl.run(sgcommon.SNAP_TITLE, cmds)
for k in range(cnt):
    fe_repl.render(os.path.join(out, 'launch_t%d.snap' % k), os.path.join(out, 'launch_t%d.png' % k))
print(o.count('state saved'), 'snapshots')
