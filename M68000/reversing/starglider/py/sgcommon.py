"""Shared paths for the Starglider scripts: the repo's M68000 directory, the work directory, the emulator DLL,
the anchor snapshots and a snapshot RAM loader. Every script walks up to the directory holding tools/rdis.py;
the work directory is scratchpad/starglider (gitignored), overridable with STARGLIDER_WORK. See ../README.md."""
import os, sys

def m68000():
    d = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(d, 'tools', 'rdis.py')):
        p = os.path.dirname(d)
        if p == d:
            raise SystemExit('repo root (the directory holding tools/rdis.py) not found')
        d = p
    return d

ROOT = os.environ.get('M68000_ROOT') or m68000()
WORK = os.environ.get('STARGLIDER_WORK') or os.path.join(ROOT, 'scratchpad', 'starglider')
DLL = os.environ.get('STARGLIDER_DLL') or os.path.join(ROOT, 'bin', 'Debug', 'net8.0', 'M68000.dll')
sys.path.insert(0, os.path.join(ROOT, 'tools'))

DISK = os.path.join(WORK, 'zuul208.st')
TEXT = 0xAB8C            # STAR.BIN runtime TEXT start (basepage $aa8c + $100); BSS ends $56264
GLOBALS = 0x5BF00        # A6 in the outer frame loop ($c9e6 lea $5bf00,A6)

def work(*p):
    return os.path.join(WORK, *p)

SNAP_TITLE = work('drive', 'g_title.snap')   # STAR.BIN title screen (drive.sh)
SNAP_GAME1 = work('drive', 'g_game1.snap')   # 40M steps after SPACE on the title: launched, in flight
SNAP_GAME2 = work('drive', 'g_game2.snap')   # 5M steps later

def load_ram(snap):
    import gfxview
    return bytes(gfxview.load_ram(snap)[0])
