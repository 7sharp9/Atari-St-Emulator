"""st.py: static snapshot reader for the Cadaver resource tables (no emulator): St(snap).obj(id) = type-6 record address, .tmpl(idx) = type-2 template, .mem(a, n).
Layout copied from verbs2/h.py (rows are 18 bytes at (A5)+96, entries are longs whose low 17 bits are the data offset)."""
import os, sys
ROOT = os.environ.get('M68000_ROOT', os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..', '..', '..')))
A5 = 0x18152
class St:
    def __init__(self, snap):
        if not os.path.isabs(snap): snap = ROOT + '/' + snap
        s = open(snap, 'rb').read(); off = 5 + 19 * 4 + 2
        self.ram = s[off + 4:off + 4 + 0x100000]
        self.desc = self.l(A5 + 96)
        self.rows = {}
        for t in range(10):
            row = self.desc + 0x12 * t
            self.rows[t] = (self.l(row), self.l(row + 4), self.w(row + 16))
    def b(self, a): return self.ram[a]
    def w(self, a): return int.from_bytes(self.ram[a:a + 2], 'big')
    def l(self, a): return int.from_bytes(self.ram[a:a + 4], 'big')
    def mem(self, a, n): return self.ram[a:a + n]
    def res(self, t, i):
        idx, dat, cnt = self.rows[t]
        e = self.l(idx + 4 * i)
        if (e >> 16) == 0: return None
        return dat + (e & 0x1ffff)
    def size(self, t, i):
        idx, dat, cnt = self.rows[t]
        return self.l(idx + 4 * i) >> 16
    def obj(self, i): return self.res(6, i)
    def tmpl(self, i): return self.res(2, i)
    def count(self, t): return self.rows[t][2]
if __name__ == '__main__':
    s = St(sys.argv[1])
    for t in range(10): print(t, [hex(x) for x in s.rows[t][:2]], s.rows[t][2])
