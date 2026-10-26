"""List the exception/MFP vectors that are not TOS 1.00's default handler, and a few system variables.

usage: vectors.py <snap>...
"""
import os, sys, struct

root = os.environ.get('M68000_ROOT') or os.path.dirname(os.path.abspath(__file__))
while not os.path.exists(os.path.join(root, 'tools', 'rdis.py')):
    root = os.path.dirname(root)
sys.path.insert(0, os.path.join(root, 'tools'))
from gfxview import load_ram

for snap in sys.argv[1:]:
    r, _ = load_ram(snap)
    print(snap)
    for v in range(2, 80):
        a = v * 4; x = struct.unpack('>I', r[a:a+4])[0]
        if (x & 0xffffff) != 0xfc0a1a: print('  vec %3d $%03x -> $%08x' % (v, a, x))
    for a in (0x400, 0x404, 0x408, 0x456, 0x4ba, 0x4ce, 0x502, 0x4d2):
        print('  sys $%03x = $%08x' % (a, struct.unpack('>I', r[a:a+4])[0]))
