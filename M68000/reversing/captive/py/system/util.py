"""Shared helpers: repo root (walk up to tools/rdis.py, or env M68000_ROOT) and snapshot RAM access."""
import os, sys, struct
def root():
    d = os.environ.get('M68000_ROOT') or os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(d, 'tools', 'rdis.py')):
        p = os.path.dirname(d)
        if p == d: raise SystemExit('repo root not found')
        d = p
    return d
sys.path.insert(0, os.path.join(root(), 'tools'))
from gfxview import load_ram  # noqa: E402
class Ram:
    def __init__(self, snap):
        self.ram, self.base = load_ram(snap)
    def b(self, a, n): return bytes(self.ram[a - self.base:a - self.base + n])
    def w(self, a): return struct.unpack('>H', self.b(a, 2))[0]
    def sw(self, a): return struct.unpack('>h', self.b(a, 2))[0]
    def l(self, a): return struct.unpack('>I', self.b(a, 4))[0]
