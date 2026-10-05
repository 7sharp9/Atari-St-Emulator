#!/usr/bin/env python3
"""a5ref.py <signed decimal or $hex offset>... : every instruction in the program ROM that addresses d16(A5) with that displacement (writers and readers).
Scans for the displacement word after an opcode word whose EA field is mode 5 reg 5 (low six bits 0x2d), directly or after one immediate word, and prints the
disassembly of the instruction. Candidates inside data show as junk: check the neighbours. Root from M68000_ROOT or __file__."""
import os, sys
here = os.path.dirname(os.path.abspath(__file__))
root = os.environ.get('M68000_ROOT') or os.path.abspath(os.path.join(here, '../../../..'))
sys.path.insert(0, os.path.join(root, 'tools'))
from disassemble import Disassembler
rom = open(os.path.join(root, 'scratchpad/finalfight/ff_main.bin'), 'rb').read()
dis = Disassembler(rom, rom_base=0)
def w(a): return int.from_bytes(rom[a:a+2], 'big')
for arg in sys.argv[1:]:
    off = int(arg[1:], 16) if arg.startswith('$') else int(arg)
    key = off & 0xffff
    for a in range(0x100, 0x100000 - 8, 2):
        if w(a) != key: continue
        for back in (2, 4, 6):
            s = a - back
            if s < 0: continue
            op = w(s)
            if (op & 0x3f) == 0x2d or ((op >> 6) & 0x3f) == 0x2d or ((op & 0xf000) in (0x1000, 0x2000, 0x3000) and (((op >> 6) & 7) == 5 and ((op >> 9) & 7) == 5)):
                try:
                    t, n = dis.decode_one(s)
                except Exception:
                    continue
                if n == a + 2 and ('(A5)' in t) and ('%d(A5)' % off) in t:
                    print('%d(A5) $%06x: %s' % (off, s, t)); break
