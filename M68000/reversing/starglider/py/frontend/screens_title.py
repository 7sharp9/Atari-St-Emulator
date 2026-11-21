"""Title attract loop: snapshot the live screen every N steps from g_title and render each (which pages alternate).
usage: screens_title.py [N=4000000] [count=8]  -> WORK/frontend/title_t<k>.snap/.png"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fe_repl, sgcommon
n = int(sys.argv[1]) if len(sys.argv) > 1 else 4000000
cnt = int(sys.argv[2]) if len(sys.argv) > 2 else 8
out = sgcommon.work('frontend')
cmds = []
for k in range(cnt):
    cmds += ['s %d' % n, 'snap %s' % os.path.join(out, 'title_t%d.snap' % k)]
o = fe_repl.run(sgcommon.SNAP_TITLE, cmds)
for k in range(cnt):
    fe_repl.render(os.path.join(out, 'title_t%d.snap' % k), os.path.join(out, 'title_t%d.png' % k))
print(o.count('state saved'), 'snapshots')
