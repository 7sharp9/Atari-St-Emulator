"""Game over -> pilot rating -> high-score entry -> STAR SCORES, driven from g_game1 with labelled pokes:
  w c098 09999999  (player-1 BCD score, $c098: beats the table at $c31e)   ww 606(A6)=1 (energy -> 'POWER DRAINAGE')
then snapshots every N steps (default 2.5M) with a render each. Typing a name uses scancodes (A=$1e, B=$30 ...).
usage: screens_gameover.py [N=2500000] [count=8] -> WORK/frontend/go_t<k>.png"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fe_repl, sgcommon
n = int(sys.argv[1]) if len(sys.argv) > 1 else 2500000
cnt = int(sys.argv[2]) if len(sys.argv) > 2 else 8
out = sgcommon.work('frontend')
cmds = ['w c098 09999999', 'ww %x 1' % (0x5BF00 + 606)]
for k in range(cnt):
    cmds += ['s %d' % n, 'snap %s' % os.path.join(out, 'go_t%d.snap' % k)]
o = fe_repl.run(sgcommon.SNAP_GAME1, cmds)
for k in range(cnt):
    fe_repl.render(os.path.join(out, 'go_t%d.snap' % k), os.path.join(out, 'go_t%d.png' % k))
print(o.count('state saved'))
