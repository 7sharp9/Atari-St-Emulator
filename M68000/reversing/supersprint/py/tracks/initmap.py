"""INIT.DAT unpacker: parse the game's own loader ($fd9a) for its (dest, len) copy sequence, then
split INIT.DAT into the A4-relative globals it initialises.  `python initmap.py` proves the split
against the RAM of the race snapshot (match count) and prints the table."""
import re, sys
sys.path.insert(0, __import__('os').path.dirname(__import__('os').path.abspath(__file__)))
from tkcommon import *

def asm_lines():
    return open(os.path.join(sscfg.WORK, 'ss.asm')).read().split('\n')

def parse_copies(lo=0xfd9a, hi=0x10000):
    seq = []; ln = None; off = None
    for l in asm_lines():
        m = re.match(r'\s+\$([0-9a-f]{6}): (.*)', l)
        if not m: continue
        a = int(m.group(1), 16)
        if a < lo or a >= hi: continue
        t = m.group(2)
        m1 = re.match(r'move\.w #\$([0-9a-f]+),-\(A7\)', t)
        if m1: ln = int(m1.group(1), 16); continue
        m2 = re.match(r'pea (-?\d+)\(A4\)', t)
        if m2: off = int(m2.group(1)); continue
        if 'jsr' in t and '$fd7a' in t: seq.append((off, ln)); ln = off = None
    return seq

def split_init():
    d = datfile('INIT.DAT'); seq = parse_copies(); pos = 0; res = []
    for off, ln in seq:
        res.append((off, ln, pos, d[pos:pos+ln])); pos += ln
    return res, pos

if __name__ == '__main__':
    res, tot = split_init()
    print('copies', len(res), 'bytes', tot, 'INIT.DAT size', len(datfile('INIT.DAT')))
    ram = load_snap(sscfg.SNAP_RACE)
    same = 0
    for off, ln, pos, b in res:
        a = A4 + off
        eq = sum(1 for i in range(ln) if ram[a+i] == b[i])
        same += eq
        print('%6d A4 %-7s $%05x len %4d (INIT+%4d) live-equal %4d/%d' % (len(res), off, a, ln, pos, eq, ln))
    print('total equal', same, 'of', tot)
