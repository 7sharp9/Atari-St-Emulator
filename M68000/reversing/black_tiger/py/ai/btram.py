"""Shared helpers: repo root, BT_WORK, snapshot RAM loading, big-endian readers."""
import os, sys, struct
def _root():
    if os.environ.get("M68000_ROOT"):
        return os.path.abspath(os.environ["M68000_ROOT"])
    d = os.path.dirname(os.path.abspath(__file__))
    while d != os.path.dirname(d):          # first ancestor holding tools/ and Program.fs (= M68000/)
        if os.path.isdir(os.path.join(d, "tools")) and os.path.exists(os.path.join(d, "Program.fs")):
            return d
        d = os.path.dirname(d)
    raise SystemExit("set M68000_ROOT")
ROOT = _root()
WORK = os.environ.get("BT_WORK") or os.path.join(ROOT, "scratchpad", "black_tiger")
OUT = os.path.join(WORK, "agents", "ai")
sys.path.insert(0, os.path.join(ROOT, "tools"))
import gfxview

def load(snap):
    p = snap if os.path.isabs(snap) else os.path.join(WORK, snap)
    ram, _ = gfxview.load_ram(p)
    return bytearray(ram)

def b(r, a): return r[a]
def sb(r, a): v = r[a]; return v - 256 if v > 127 else v
def w(r, a): return (r[a] << 8) | r[a + 1]
def sw(r, a): v = w(r, a); return v - 65536 if v > 32767 else v
def l(r, a): return struct.unpack_from(">I", r, a)[0]
