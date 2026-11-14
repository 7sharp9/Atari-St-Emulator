import sys, struct, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../../../tools"))
import gfxview
def load(p): return gfxview.load_ram(p)[0]
class R:
    def __init__(s, p): s.m = load(p)
    def b(s,a): return s.m[a]
    def w(s,a): return struct.unpack_from(">H", s.m, a)[0]
    def sw(s,a): return struct.unpack_from(">h", s.m, a)[0]
    def l(s,a): return struct.unpack_from(">I", s.m, a)[0]
    def sl(s,a): return struct.unpack_from(">i", s.m, a)[0]
