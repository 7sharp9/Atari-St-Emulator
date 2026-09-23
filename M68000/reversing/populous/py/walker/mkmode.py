"""mkmode.py <snap_in> <icon> <snap_out> : click a panel icon through popdrive, report side modes."""
import os, sys
sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')))
from popdrive import Game, plan_icon, run
from popmem import ram, w
snap_in, icon, snap_out = [os.path.abspath(a) if a.endswith(".snap") else a for a in sys.argv[1:4]]
g = Game(ram(snap_in))
lines, info = plan_icon(g, icon)
run(snap_in, lines, snap_out)
m = ram(snap_out)
print(icon, info, 'frame', w(m, 0x3c4c8), 'mode side0', w(m, 0x3b22a), 'side1', w(m, 0x3b23a))
