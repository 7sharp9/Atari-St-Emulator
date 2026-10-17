"""usage: stepsnap.py <src.snap> <steps> <dst.snap> : resume, step, save a snapshot (one emulator process)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rcommon import *
from repl import Repl
src, steps, dst = sys.argv[1], int(sys.argv[2]), sys.argv[3]
r = Repl(src)
r.cmd('s %d' % steps)
out, regs = r.cmd('snap %s' % dst)
r.close()
print('wrote', dst)
