"""Shared paths for the Virus scripts: the repo's M68000 directory, the work directory and the snapshot loader.
Every script walks up to the directory holding tools/rdis.py; the work directory is scratchpad/virus (gitignored),
overridable with the VIRUS_WORK environment variable."""
import os, sys

def m68000():
    d = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(d, 'tools', 'rdis.py')):
        p = os.path.dirname(d)
        if p == d:
            raise SystemExit('repo root (the directory holding tools/rdis.py) not found')
        d = p
    return d

ROOT = m68000()
WORK = os.environ.get('VIRUS_WORK') or os.path.join(ROOT, 'scratchpad', 'virus')
sys.path.insert(0, os.path.join(ROOT, 'tools'))

def work(*p):
    return os.path.join(WORK, *p)

def load_ram(snap):
    import gfxview
    return bytes(gfxview.load_ram(snap)[0])
