"""Shared helpers for the Captive AI scripts (reversing/captive/ai.md): repo root (walk up to tools/rdis.py, or
env M68000_ROOT), stserver, federation globals (A6 = $1b5ce). A relative snapshot path is tried under
scratchpad/captive/, then under the repo root. OUT is where scripts write snapshots."""
import os, sys, struct

def root():
    d = os.environ.get('M68000_ROOT') or os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(d, 'tools', 'rdis.py')):
        nd = os.path.dirname(d)
        if nd == d:
            sys.exit('repo root (tools/rdis.py) not found')
        d = nd
    return d

R = root()
sys.path.insert(0, os.path.join(R, 'tools'))
from stclient import StServer  # noqa: E402

A6 = 0x1b5ce
W = os.path.join(R, 'scratchpad', 'captive')
OUT = os.path.join(W, 'agents', 'ai')

def snappath(snap):
    """Absolute path for a snapshot argument: as given if absolute, else under scratchpad/captive/, else the repo root."""
    return snap if os.path.isabs(snap) else os.path.join(W, snap) if os.path.exists(os.path.join(W, snap)) else os.path.join(R, snap)

def srv(snap):
    s = StServer(R)
    s('load', snapshot=snappath(snap))
    return s

def w16(s, off):
    return struct.unpack('>h', s.read(A6 + off, 2))[0]

def l32(s, off):
    return struct.unpack('>I', s.read(A6 + off, 4))[0]
