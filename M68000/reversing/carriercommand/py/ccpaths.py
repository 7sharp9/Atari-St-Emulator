"""Shared paths for the Carrier Command scripts.

ROOT is the M68000/ directory (found by walking up to tools/rdis.py, or $M68000_ROOT); WORK is the
untracked data directory, $CARRIER_WORK or ROOT/scratchpad/carrier. Scripts in py/<area>/ import this
module from one directory up:

    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent)); from ccpaths import *
"""
import os
import pathlib
import sys


def _root():
    env = os.environ.get('M68000_ROOT')
    if env:
        return pathlib.Path(env)
    for q in pathlib.Path(__file__).resolve().parents:
        if (q / 'tools' / 'rdis.py').exists():
            return q
    raise SystemExit('ccpaths: cannot find the M68000 root (tools/rdis.py); set M68000_ROOT')


ROOT = _root()
WORK = pathlib.Path(os.environ.get('CARRIER_WORK', ROOT / 'scratchpad' / 'carrier'))
DLL = ROOT / 'bin' / 'Debug' / 'net8.0' / 'M68000.dll'
ANCHOR = WORK / 'c_s30.snap'          # strategy game, carrier at VULCAN (README "Snapshots")

_cache = {}


def ram(snap=ANCHOR):
    """The 1 MB RAM image of a .snap as bytes (address = offset); a non-.snap path is read raw."""
    snap = str(snap)
    if snap not in _cache:
        sys.path.insert(0, str(ROOT / 'tools'))
        from gfxview import load_ram
        _cache[snap] = bytes(load_ram(snap)[0])
    return _cache[snap]


def area_dir(name):
    d = WORK / name
    d.mkdir(parents=True, exist_ok=True)
    return d
