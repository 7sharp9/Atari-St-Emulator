"""Find bodies named like PHOOPEL across missions, with their target numbers (universe.py model)."""
import sys, os
import os as _os
_M = _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '../../../..'))  # M68000/
sys.path.insert(0, _M + '/reversing/captive/py/world')
import universe as U
import struct
ram, base = U.load_ram(_M + '/scratchpad/captive/star.snap')
xytab = list(ram[0x3047c:0x3047c + 32])
orbtab = [struct.unpack('>hh', ram[0x303d6+4*i:0x303d6+4*i+4]) for i in range(8)]
pat = sys.argv[1] if len(sys.argv) > 1 else 'PHOOPEL'
maxm = int(sys.argv[2]) if len(sys.argv) > 2 else 200
for m in range(maxm):
    objs = None
    for i in range(150):
        n = U.name(ram, m, i)
        if n == pat or (pat.startswith('~') and pat[1:] in n):
            if objs is None:
                objs = U.generate(m, xytab, orbtab)[4]
            print(f'mission index {m} (MISSION {m+1:04d}) obj {i} slot {i+1} {"PLANET" if i<50 else "MOON"}-{n} target={objs[i][3]} bytes={objs[i]}')
