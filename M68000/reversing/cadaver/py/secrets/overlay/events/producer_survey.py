"""a3: producer_survey.py [steps] snap...  : no-input run of each snapshot with `hits` on the eight producer push sites (event 1 $a114 $fa62, 4 $f328, 10 $9286, 11 $f69c,
12 $f9a2, 13 $b0f0, 25 $f0c8) and the consumer ($fdbc entry, $fe24 event byte matched a block, $fe36 gate passed, $fe5a verb dispatch).  Run from M68000/."""
import sys, os
ROOT = os.environ.get('M68000_ROOT') or os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../../../../..'))
os.chdir(ROOT)
sys.path.insert(0, ROOT + '/reversing/cadaver/py/secrets')
from repl import Repl
PROD = {'a114': 1, 'fa62': 1, 'f328': 4, '9286': 10, 'f69c': 11, 'f9a2': 12, 'b0f0': 13, 'f0c8': 25}
CONS = {'fdbc': 'cons', 'fe24': 'match', 'fe36': 'gate', 'fe5a': 'verb'}
args = sys.argv[1:]
steps = int(args[0]) if args and args[0].isdigit() else 3000000
snaps = [a for a in args if not a.isdigit()]
for s in snaps:
    r = Repl(os.path.abspath(s))
    addrs = [int(a, 16) for a in list(PROD) + list(CONS)]
    h = r.hits(steps, *addrs)
    print('%-60s %s' % (s[-60:], ' '.join('%s(e%d)=%d' % (a, PROD[a], h.get(int(a, 16), 0)) for a in PROD) + ' | ' + ' '.join('%s=%d' % (CONS[a], h.get(int(a, 16), 0)) for a in CONS)), flush=True)
    r.close()
