"""a3: dump the type-6 template bytes (+0..+0x50) of object ids: python tmpl.py <snap> <id>...  (static, from the snapshot file)"""
import sys, os
ROOT = os.environ.get('M68000_ROOT') or os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../../../../..'))
sys.path.insert(0, ROOT + '/reversing/cadaver/py/secrets/overlay/verbs2')
snap = os.path.abspath(sys.argv[1]); ids = [int(x) for x in sys.argv[2:]]
import h as H
class S(H.H):
    def __init__(self, snap):
        self.snap = snap
        self.desc = 0x18152 + 96 if False else None
        s = open(snap, 'rb').read(); off = 5 + 19 * 4 + 2
        self.ram = s[off + 4:off + 4 + 0x100000]
        self.desc = int.from_bytes(self.ram[H.A5 + 96:H.A5 + 100], 'big')
        self._load_static()
h = S(snap)
for i in ids:
    a = h.obj(i)
    print('obj %d @%06x' % (i, a), h.ram[a:a + 0x50].hex(' '))
