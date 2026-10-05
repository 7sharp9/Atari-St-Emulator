"""Print the frames where $80040 / $80041 (F line columns f40 f41) or the level byte change. usage: flags.py <objlog.txt> [from] [to]"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import ol
f0 = int(sys.argv[2]) if len(sys.argv) > 2 else 0
f1 = int(sys.argv[3]) if len(sys.argv) > 3 else 1 << 30
prev = None
for fr in ol.frames(sys.argv[1]):
    k = (fr["f40"], fr["f41"], fr["lvl"])
    if k != prev and f0 <= fr["f"] <= f1:
        print(f"f{fr['f']} sx={fr['sx']:04x} f40={fr['f40']:02x} f41={fr['f41']:02x} lvl={fr['lvl']} nA={fr['n']}")
    prev = k
