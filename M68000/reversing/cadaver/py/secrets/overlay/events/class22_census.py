"""a3: class22_census.py <snap> : byte 22 of the type-2 class template of every type-6 record (the 'class' the mover step $00f9b8 tests: bit 7 set = projectile-like; $80/$81/$84 have their own hit paths, others run the generic hit loop that pushes event 1).  Static."""
import sys, os, collections
ROOT = os.environ.get('M68000_ROOT') or os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../../../../..'))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from second_list_alias import S
snap = os.path.abspath(sys.argv[1]); h = S(snap)
cnt = collections.defaultdict(list)
for i in range(1000):
    a = h.obj(i)
    if a is None: continue
    cid = int.from_bytes(h.ram[a + 6:a + 8], 'big'); ca = h.res(2, cid)
    if ca is None: continue
    cnt[h.ram[ca + 22]].append(i)
for k in sorted(cnt): print('class byte 22 = $%02x: %d objects %s' % (k, len(cnt[k]), cnt[k][:30]))
