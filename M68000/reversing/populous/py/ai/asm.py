"""asm.py START END : print pop_ad58.asm lines with START <= addr < END (hex)."""
import sys, os
sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')))
from popcfg import WORK
a, b = int(sys.argv[1], 16), int(sys.argv[2], 16)
for line in open(os.path.join(WORK, 'pop_ad58.asm')):
    try: x = int(line[:6], 16)
    except ValueError: continue
    if a <= x < b: print(line, end='')
    elif x >= b: break
