#!/usr/bin/env python3
"""List instructions in the ROM that use d16(A5) with the given displacement (decimal or $hex; negative allowed), by scanning for opcode words whose EA is mode 5 reg 5 (low 6 bits 0x2d) or the
destination field of a move (bits 11..6 = 0b101101) followed by the displacement word. Heuristic (no instruction sizing): confirm with the listing.
usage: a5refs.py <disp> [lo hi]"""
import os, sys
here = os.path.dirname(os.path.abspath(__file__))
root = os.environ.get('M68000_ROOT') or os.path.abspath(os.path.join(here, '..', '..', '..', '..'))
rom = open(os.path.join(root, 'scratchpad', 'finalfight', 'ff_main.bin'), 'rb').read()
w = lambda a: int.from_bytes(rom[a:a+2], 'big')
def main():
    d = sys.argv[1]; d = int(d[1:], 16) if d.startswith('$') else int(d)
    d &= 0xffff
    lo = int(sys.argv[2], 16) if len(sys.argv) > 2 else 0
    hi = int(sys.argv[3], 16) if len(sys.argv) > 3 else 0x64000
    for a in range(lo, hi - 4, 2):
        for k in (2, 4, 6):   # extension word position relative to opcode
            if a + k <= len(rom) - 2 and w(a + k) == d:
                op = w(a)
                ea_src = op & 0x3f
                ea_dst = ((op >> 3) & 0x38) | ((op >> 9) & 7)   # move: mode in bits 8..6, reg in bits 11..9
                dst_mode = (op >> 6) & 7; dst_reg = (op >> 9) & 7
                hit = (ea_src == 0x2d and k == 2) or ((op & 0xc000) == 0 and (op & 0x3000) != 0 and dst_mode == 5 and dst_reg == 5 and ((k == 4 and (ea_src >> 3) in (0,1,2,3,4,7)) or k == 2))
                if hit: print('%06x: %04x %04x' % (a, op, w(a + 2)))
                break
main()
