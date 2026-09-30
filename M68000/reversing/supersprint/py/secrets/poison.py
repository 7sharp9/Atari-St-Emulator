"""poison.py SNAP LO HI STEPS [pattern]: A/B poison test.  Run SNAP for STEPS with and without bytes LO..HI overwritten by a
pattern (default ab); dump all RAM at the end of both runs and report the bytes that differ outside [LO,HI).  Zero differing
bytes = nothing running in STEPS consumed that region (deterministic emulator; see detcheck)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ssh import *
from multiprocessing import Pool

def run(args):
    snap, lo, hi, steps, pat, poisoned = args
    r = R(snap)
    if poisoned:
        for a in range(lo & ~3, (hi + 3) & ~3, 4):
            r.cmd('w %x %s' % (a, pat * 4))
    r.cmd('s %d' % steps)
    data = bytearray()
    a = 0x200
    while a < 0x100000:
        n = min(0x10000, 0x100000 - a)
        data += r.mem(a, n); a += n
    r.close()
    return bytes(data)

def ab(snap, lo, hi, steps, pat='ab'):
    with Pool(2) as p:
        base, pois = p.map(run, [(snap, lo, hi, steps, pat, False), (snap, lo, hi, steps, pat, True)])
    diff = [i + 0x200 for i in range(len(base)) if base[i] != pois[i] and not (lo <= i + 0x200 < hi)]
    return diff

if __name__ == '__main__':
    snap = sys.argv[1]; lo = int(sys.argv[2], 16); hi = int(sys.argv[3], 16); steps = int(sys.argv[4])
    pat = sys.argv[5] if len(sys.argv) > 5 else 'ab'
    d = ab(snap, lo, hi, steps, pat)
    print('region %x-%x pattern %s steps %d: %d bytes differ outside the region' % (lo, hi, pat, steps, len(d)))
    if d:
        print('first diffs:', ['%x' % x for x in d[:16]])
