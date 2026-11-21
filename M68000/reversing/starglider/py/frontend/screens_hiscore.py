"""From the pilot-rating screen (go_t2.snap of screens_gameover.py): tap SPACE, then snapshot every N steps.
Writes WORK/frontend/hs_t<k>.snap/.png.   usage: screens_hiscore.py [N=1500000] [count=6]"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fe_repl, sgcommon
n = int(sys.argv[1]) if len(sys.argv) > 1 else 1500000
cnt = int(sys.argv[2]) if len(sys.argv) > 2 else 6
out = sgcommon.work('frontend')
cmds = fe_repl.key('39', 200000)
for k in range(cnt):
    cmds += ['s %d' % n, 'snap %s' % os.path.join(out, 'hs_t%d.snap' % k)]
o = fe_repl.run(os.path.join(out, 'go_t2.snap'), cmds)
for k in range(cnt):
    fe_repl.render(os.path.join(out, 'hs_t%d.snap' % k), os.path.join(out, 'hs_t%d.png' % k))
print(o.count('state saved'))
