"""flow.py - A/B poison harness.  A flow = (snapshot, script).  A script is a list of REPL command strings; the pseudo-command
'!dump' dumps RAM 0x200..0x100000 (a checkpoint).  A variant = list of SUPER.DAT file-offset ranges (lo, hi) overwritten with
the pattern before the script runs (None = clean).  consumed(variant) = number of RAM bytes that differ from the clean run
outside the poisoned ranges at any checkpoint.  Deterministic emulator, same script and budget for every variant.

    python3 flow.py SNAP 'SCRIPT' [lo-hi ...]       SCRIPT: commands separated by ';' ('s 3000000;!dump')
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from uc import *
from multiprocessing import Pool

def dump(r):
    d = bytearray(); a = 0x200
    while a < 0x100000:
        n = min(0x10000, 0x100000 - a); d += r.mem(a, n); a += n
    return bytes(d)

def run_one(args):
    snap, script, ranges, pat = args
    r = Repl2(snap)
    regs = {}
    if ranges:
        lines = []
        for lo, hi in ranges:
            for a in range(BUF + (lo & ~3), BUF + ((hi + 3) & ~3), 4):
                lines.append('w %x %s' % (a, pat * 4))
        for i in range(0, len(lines), 2000): r.cmd('\n'.join(lines[i:i + 2000]))
    dumps = []
    for c in script:
        if c == '!dump': dumps.append(dump(r))
        elif c.startswith('!bpc '):                      # '!bpc ADDR MAXSTEPS': run to ADDR (first hit)
            _, a, m = c.split(); o, regs = r.cmd2('bpc %s 1 %s' % (a, m))
            if regs.get('PC') != int(a, 16): raise RuntimeError('bpc %s not reached (PC=%x)' % (a, regs.get('PC', 0)))
        elif c.startswith('!pokew '):                    # '!pokew A6-2 3' or '!pokew 1eb44 3': 16-bit word via read-modify-write
            _, a, v = c.split()
            ad = (regs['A6'] + int(a[2:], 0)) if a.startswith('A6') else int(a, 16)
            old = r.mem(ad, 4)
            r.cmd('w %x %04x%s' % (ad, int(v, 0), old[2:].hex()))
        else: r.cmd(c)
    # return also the final PC for diagnostics
    _, regs = r.cmd('')
    r.close()
    return dumps, regs.get('PC')

def diffs(clean, dumps, ranges):
    """list of (checkpoint, count outside the poisoned ranges, first addrs)"""
    import numpy as np
    ex = [(BUF + (lo & ~3), BUF + ((hi + 3) & ~3)) for lo, hi in (ranges or [])]      # the poke writes whole longwords
    res = []
    for k, (c, d) in enumerate(zip(clean, dumps)):
        m = np.frombuffer(c, np.uint8) != np.frombuffer(d, np.uint8)
        for lo, hi in ex: m[lo - 0x200:hi - 0x200] = False
        idx = np.nonzero(m)[0]
        res.append((k, int(len(idx)), [int(i) + 0x200 for i in idx[:6]]))
    return res

def consumed(snap, script, variants, pat='ab', procs=3):
    """variants: list of range-lists.  Returns (clean_pc, [(ranges, total, per-checkpoint)])"""
    jobs = [(snap, script, None, pat)] + [(snap, script, v, pat) for v in variants]
    with Pool(procs) as p:
        outs = p.map(run_one, jobs)
    clean, cpc = outs[0]
    res = []
    for v, (dm, pc) in zip(variants, outs[1:]):
        ds = diffs(clean, dm, v)
        res.append((v, sum(x[1] for x in ds), ds, pc))
    return cpc, res

def parse_script(s):
    return [x.strip() for x in s.split(';') if x.strip()]

if __name__ == '__main__':
    snap = sys.argv[1]; script = parse_script(sys.argv[2])
    snap = snapath(snap)
    vs = [[tuple(int(x, 16) for x in a.split('-'))] for a in sys.argv[3:]]
    cpc, res = consumed(snap, script, vs)
    print('clean final PC %x' % cpc)
    for v, tot, ds, pc in res:
        print('poison', ['%x-%x' % t for t in v], 'diff', tot, [(k, n, ['%x' % a for a in f]) for k, n, f in ds], 'pc %x' % pc)
