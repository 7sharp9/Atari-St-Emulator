"""Shared helpers for the `engine` agent scripts (paths via sscfg; snapshot RAM via tools/gfxview)."""
import os, sys, struct


def _find_root():
    """M68000/ = the first ancestor that contains reversing/supersprint/py/sscfg.py (works from scratchpad/.../agents/engine/py and from
    reversing/supersprint/py/engine); M68000_ROOT overrides."""
    if os.environ.get('M68000_ROOT'):
        return os.environ['M68000_ROOT']
    d = os.path.dirname(os.path.abspath(__file__))
    while True:
        if os.path.exists(os.path.join(d, 'reversing', 'supersprint', 'py', 'sscfg.py')):
            return d
        nd = os.path.dirname(d)
        if nd == d:
            raise SystemExit('cannot find M68000/ (set M68000_ROOT)')
        d = nd


ROOT = _find_root()
sys.path.insert(0, os.path.join(ROOT, 'reversing', 'supersprint', 'py'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import sscfg
from gfxview import load_ram, load_video_regs
OUT = os.environ.get('ENGINE_OUT') or os.path.join(sscfg.WORK, 'agents', 'engine')    # generated data (PNGs, logs, sound)
PNG = os.path.join(OUT, 'png')
os.makedirs(PNG, exist_ok=True)
A4 = sscfg.A4


class Ram:
    def __init__(s, path):
        s.b, _ = load_ram(path)
    def w(s, a):  return struct.unpack_from('>H', s.b, a)[0]
    def sw(s, a): return struct.unpack_from('>h', s.b, a)[0]
    def l(s, a):  return struct.unpack_from('>I', s.b, a)[0]
    def g(s, off):  return s.l(A4 + off)        # long global at off(A4)
    def gw(s, off): return s.w(A4 + off)
    def gsw(s, off): return s.sw(A4 + off)


def st_rgb(word):
    """STF 3-bit-per-channel colour word -> 8-bit RGB with the emulator's own scaling (7 -> 255), as in its frame recorder."""
    r, g, b = (word >> 8) & 7, (word >> 4) & 7, word & 7
    return tuple(v * 255 // 7 for v in (r, g, b))


def palette_at(ram, addr, n=16):
    return [st_rgb(ram.w(addr + 2 * i)) for i in range(n)]


def decode_st_screen(buf, pal, w=320, h=200, off=0):
    """ST low-res interleaved 4-plane screen memory -> PIL image (palette = list of 16 (r,g,b))."""
    from PIL import Image
    img = Image.new('RGB', (w, h)); px = img.load()
    for y in range(h):
        for xw in range(0, w, 16):
            o = off + y * (w // 2) + (xw // 16) * 8
            pl = [struct.unpack_from('>H', buf, o + 2 * p)[0] for p in range(4)]
            for bit in range(16):
                sh = 15 - bit
                idx = sum(((pl[p] >> sh) & 1) << p for p in range(4))
                px[xw + bit, y] = pal[idx]
    return img
