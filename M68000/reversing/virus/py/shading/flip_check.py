"""Gate: $183f2 is the page flip.  Twice from the snapshot: `bp 183f2`, dump $62a5a (1 byte) and $2705e..$27069 (draw/display
pointers), step 60, dump again.  Expected: $62a5a toggles ff<->00 and $2705e/$27062 alternate $78000/$78a00 <-> $70000/$70a00.
Usage: flip_check.py <snap>"""
import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
t = repl(sys.argv[1], ['bp 183f2 3000000', 'm 62a5a 1', 'm 2705e 12', 's 60', 'm 62a5a 1', 'm 2705e 12'] * 2)
dumps = [l.strip() for l in t.split('\n') if re.fullmatch(r'([0-9a-f]{2} )*[0-9a-f]{2}', l.strip())]
st = [(dumps[i], dumps[i + 1]) for i in range(0, len(dumps), 2)]       # (flag, pointers) x4: before, after, before2, after2
ok = 0
for i in (0, 2):
    b, a = st[i], st[i + 1]
    ok += b[0] != a[0] and b[1].split()[:4] != a[1].split()[:4] and {b[1].split()[1], a[1].split()[1]} == {'07'} \
        and {b[1].split()[2], a[1].split()[2]} == {'00', '80'}
print('page flips toggling $62a5a and swapping $2705e between $70000 and $78000: %d/2' % ok)
