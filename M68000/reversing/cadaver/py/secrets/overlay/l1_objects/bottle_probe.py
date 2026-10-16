"""pr.py SNAP: fire probe in front; print front object, icons"""
import sys, os
d = os.path.abspath(os.path.dirname(__file__))
while not os.path.exists(d + '/tools/rdis.py'): d = os.path.dirname(d)
ROOT = os.environ.get('M68000_ROOT', d); snap = os.path.abspath(sys.argv[1])
sys.path.insert(0, ROOT + '/reversing/cadaver/py/secrets/overlay/action/exit_level0/g2')
from lib import *
r = Repl(snap); print(st(r))
res = probe(r); print('probe', res, 'front 2128', r.w(A5 + 2128))
r.close()
