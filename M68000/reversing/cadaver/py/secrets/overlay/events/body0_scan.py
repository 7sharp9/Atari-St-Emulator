"""a3: body0_scan.py <snap> <byte> : ids of type-6 records whose body byte 0 (record + byte at +12) equals <byte>; gate of event 1 compares an operand against this byte of object id = entry word.  Static."""
import sys, os
ROOT = os.environ.get('M68000_ROOT') or os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../../../../..'))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT + '/reversing/cadaver/py/secrets/overlay/verbs2')
from second_list_alias import S  # noqa (prints alias report on import; harmless)
snap = os.path.abspath(sys.argv[1]); want = int(sys.argv[2], 0)
h = S(snap)
ids = []
for i in range(1000):
    a = h.obj(i)
    if a is None: continue
    b = h.ram[a + h.ram[a + 12]]
    if b == want: ids.append(i)
print(len(ids), ids)
