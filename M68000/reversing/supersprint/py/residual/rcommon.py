"""Shared setup for the `residual` agent scripts: repo root via sscfg, access to the engine/ modules (read-only), output dir."""
import os, sys, struct
_d = os.path.dirname(os.path.abspath(__file__))
while not os.path.exists(os.path.join(_d, 'reversing', 'supersprint', 'py', 'sscfg.py')):
    _n = os.path.dirname(_d)
    if _n == _d: raise SystemExit('cannot find M68000/ (set M68000_ROOT)')
    _d = _n
ROOT = os.environ.get('M68000_ROOT') or _d
sys.path.insert(0, os.path.join(ROOT, 'reversing', 'supersprint', 'py'))
sys.path.insert(0, os.path.join(ROOT, 'reversing', 'supersprint', 'py', 'engine'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import sscfg
AGENT = os.path.join(sscfg.WORK, 'agents', 'residual')
OUT = os.path.join(AGENT, 'out'); os.makedirs(OUT, exist_ok=True)
SNAP = os.path.join(AGENT, 'snap'); os.makedirs(SNAP, exist_ok=True)

os.environ.setdefault('ENGINE_OUT', os.path.join(AGENT, 'engine_out'))   # engine/common.py makes png/ under this; keep it inside our dir
