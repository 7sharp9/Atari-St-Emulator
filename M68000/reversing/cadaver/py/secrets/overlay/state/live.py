"""live.py: helpers to inspect the live sprite array / object records over the REPL (read-only unless a poke is called).
Sprite array: 70-byte entries at l(A5+56), count w(A5+1152); entry +6 template ptr, +10 record ptr, +42 draw state, +22 flags.  Record = type-6 live record."""
import os, sys
ROOT = os.environ.get('M68000_ROOT', os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..', '..', '..')))
os.chdir(ROOT)
OUTDIR = os.path.abspath(os.environ.get('OUTDIR', ROOT + '/scratchpad/cadaver/s91_state'))   # outputs, temp files and sample lists of this directory's scripts
os.makedirs(OUTDIR, exist_ok=True)
sys.path.insert(0, ROOT + '/reversing/cadaver/py/secrets'); sys.path.insert(0, ROOT + '/reversing/cadaver/py/secrets/overlay')
from repl import Repl, A5
from ov import wb, ww, wl

def SN(key, default):
    """snapshot path: environment SNAP_<key> overrides the default lineage snapshot"""
    return os.environ.get('SNAP_' + key, default)

def start(snap):
    snap = snap if os.path.isabs(snap) else os.path.abspath(os.path.join(ROOT, snap))
    return Repl(snap)

def entries(r):
    base = r.l(A5 + 56); n = r.w(A5 + 1152)
    raw = r.mem(base, 70 * n)
    out = []
    for i in range(n):
        e = raw[70 * i:70 * i + 70]
        w0 = int.from_bytes(e[0:2], 'big')
        if w0 >= 0x8000: continue
        out.append(dict(slot=i, addr=base + 70 * i, raw=e, tmpl=int.from_bytes(e[6:10], 'big'), rec=int.from_bytes(e[10:14], 'big')))
    return out

def rec_of(r, a, n=64):
    return r.mem(a, n)

def objs(r):
    """list of dicts for live objects: id, record address, header bytes, template flags/class"""
    res = []
    for e in entries(r):
        ra = e['rec']
        if not (0x10000 < ra < 0x100000): continue
        rec = r.mem(ra, 16)
        ta = e['tmpl']; t = r.mem(ta, 32)
        res.append(dict(slot=e['slot'], ent=e['addr'], id=int.from_bytes(rec[4:6], 'big'), rec=ra, hdr=rec, tm=t, e=e['raw']))
    return res
