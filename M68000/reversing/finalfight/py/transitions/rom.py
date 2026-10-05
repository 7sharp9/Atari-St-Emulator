"""rom.py: read the Final Fight program ROM (scratchpad/finalfight/ff_main.bin). The repo root is found by walking up from this file (or M68000_ROOT)."""
import os
def _root():
    r = os.environ.get('M68000_ROOT')
    if r: return r
    d = os.path.dirname(os.path.abspath(__file__))
    while d != '/':
        if os.path.exists(os.path.join(d, 'scratchpad/finalfight/ff_main.bin')): return d
        d = os.path.dirname(d)
    raise SystemExit('repo root (scratchpad/finalfight/ff_main.bin) not found; set M68000_ROOT')
ROOT = _root()
ROM = open(os.path.join(ROOT, 'scratchpad/finalfight/ff_main.bin'), 'rb').read()
def rb(a): return ROM[a]
def rw(a): return (ROM[a] << 8) | ROM[a + 1]
def rsw(a):
    v = rw(a); return v - 0x10000 if v & 0x8000 else v
def rl(a): return (rw(a) << 16) | rw(a + 2)
NAREAS = [rb(0x54c0 + s) for s in range(10)]   # areas per stage, $54b4 reads $54c0 + stage
