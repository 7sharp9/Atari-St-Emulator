"""scan_keys.py SNAP TAG [--steps N] : exhaustive scancode scan.  From SNAP, for every scancode 0x01..0x75 (make, hold 60000
steps, break, then run to N total steps) count entries of the high-level screen routines; report every scancode whose
count-vector differs from the no-key baseline.  Workers run in parallel (one emulator each)."""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from probe import *
from multiprocessing import Pool

ENTRIES = {  # screen-level routine entries (all `link A6`/thunk targets read from ss.asm)
    0x13a5e: 'session', 0x18b54: 'options', 0x19164: 'select-track', 0x18024: 'prepare', 0xbe40: 'race',
    0xcaa8: 'demo-race', 0x1a4ca: 'winner', 0x172f0: 'hiscore-entry', 0x19984: 'shop', 0x1b7e2: 'lap-records',
    0x1bc92: 'all-time-bests', 0x1b458: 'thunk534', 0x13a44: 'title-draw', 0x103e6: 'reset-hook-install',
    0x10430: 'reset-hook-run', 0x1399e: 'wait-loop-entry',
}
ADDRS = list(ENTRIES)

def run_one(args):
    snap, code, steps, pre = args
    r = R(snap)
    try:
        if pre: r.cmd('s %d' % pre)
        a = Acc(r, ADDRS)
        if code is not None:
            a.press(['%02x' % code], 60000)
            a.run(steps - 60000)
        else:
            a.run(steps)
        return code, {hex(k): v for k, v in a.tot.items() if v}
    finally:
        r.close()

if __name__ == '__main__':
    snap = sys.argv[1]; tag = sys.argv[2]
    steps = int(sys.argv[sys.argv.index('--steps') + 1]) if '--steps' in sys.argv else 3000000
    pre = int(sys.argv[sys.argv.index('--pre') + 1]) if '--pre' in sys.argv else 0
    codes = [None] + list(range(1, 0x76))
    with Pool(6) as p:
        res = dict(p.map(run_one, [(snap, c, steps, pre) for c in codes]))
    base = res[None]
    print('baseline', base)
    diff = {}
    for c in range(1, 0x76):
        if res[c] != base:
            diff[c] = res[c]
    out = {'baseline': base, 'diff': {'%02x' % c: v for c, v in diff.items()}, 'n': len(codes) - 1}
    json.dump(out, open(os.path.join(AGENT, 'scan_%s.json' % tag), 'w'), indent=1)
    print('scancodes tested', len(codes) - 1, 'differing from baseline:', ['%02x' % c for c in diff])
    for c, v in diff.items():
        print('  %02x' % c, v)
