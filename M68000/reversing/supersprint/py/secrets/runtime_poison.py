"""runtime_poison.py SNAP STEPS LO HI BLOCK [TAG] - runtime poison scan of the in-place SUPER.DAT graphics buffer.
For every BLOCK-byte block of RAM [LO,HI): poison it in SNAP, run STEPS (RAM dumped at 3 equally spaced checkpoints), compare with
the clean run; report blocks whose poisoning changes RAM outside the block at any checkpoint.  Output: JSON + table."""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ssh import *
from multiprocessing import Pool

def dump(r):
    data = bytearray(); a = 0x200
    while a < 0x100000:
        n = min(0x10000, 0x100000 - a); data += r.mem(a, n); a += n
    return bytes(data)

def run(args):
    snap, steps, lo, hi, pat = args[:5]
    SCRIPT = args[5] if len(args) > 5 else []
    r = R(snap)
    if lo is not None:
        for a in range(lo & ~3, (hi + 3) & ~3, 4): r.cmd('w %x %s' % (a, pat * 4))
    for c in SCRIPT: r.cmd(c)
    dumps = []
    for k in range(3):
        r.cmd('s %d' % (steps // 3)); dumps.append(dump(r))
    r.close()
    return dumps

if __name__ == '__main__':
    snap = sys.argv[1]; steps = int(sys.argv[2]); B = int(sys.argv[5], 16)
    # LO/HI may be comma-separated lists of ranges: 28e00,37e00 / 2ce00,38e00
    LOS = [int(x, 16) for x in sys.argv[3].split(',')]; HIS = [int(x, 16) for x in sys.argv[4].split(',')]
    tag = sys.argv[6] if len(sys.argv) > 6 else 'x'
    SCRIPT = [x for x in sys.argv[7].split(';') if x] if len(sys.argv) > 7 else []   # e.g. 's 1000000;kbd fe 80;s 60000;kbd fe 00'
    snap = getattr(sscfg, snap) if hasattr(sscfg, snap) else snap
    clean = run((snap, steps, None, None, 'ab', SCRIPT))
    blocks = [(a, min(a + B, hi_)) for lo_, hi_ in zip(LOS, HIS) for a in range(lo_, hi_, B)]
    res = []
    with Pool(6) as p:
        for (lo, hi), d in zip(blocks, p.imap(run, [(snap, steps, lo, hi, 'ab', SCRIPT) for lo, hi in blocks])):
            nd = 0
            for k in range(3):
                nd += sum(1 for i in range(len(clean[k])) if clean[k][i] != d[k][i] and not (lo <= i + 0x200 < hi))
            res.append({'lo': lo, 'hi': hi, 'diff': nd})
            print('%06x-%06x (file +%06x) diff outside %d' % (lo, hi, lo - 0x28e00, nd), flush=True)
    json.dump(res, open(os.path.join(AGENT, 'runtime_poison_%s.json' % tag), 'w'), indent=1)
