"""Run fed_MapGen's body with chosen arguments and dump its grids (reversing/captive/mapgen.md, "Call interface").

    uv run python -I reversing/captive/py/mapgen/gen.py <out.json> d0,d1,d2,d3 [d0,d1,d2,d3 ...]

From scratchpad/captive/mg_ret.snap (the landing call's natural return; the module is at $1f7b0, its variables at
A6 = $20376), each case loads the snapshot afresh, sets D0-D3, D4 = -1, A0 = $1d9e8 (federation 9242(A6)),
A1 = $b532 (federation's pointer-offset table), A2 = $303c, and calls $20054 (the `tst.w D4` after the prologue's
register reload at $2004e) from a planted return address. These are labelled pokes: the registers are the caller's
($b5a8-$b5c0), the entry skips the Copylock prologue (which is the part that reads the disk). With MAPGEN_POISON=1
every output region is filled with $5a first, so an equal read afterwards was written by the call.

Per case the json holds the steps, D0-D7/A0-A2 at return and hex of: g0 = 56(A6) (64x32 words), g1 = 4168(A6),
g2 = 8280(A6) (64x32 byte pairs), outa = $1d9e8 and outb = $1e208 (federation's two 64x32 byte layers), vars =
module bytes 0..55, fedtab = $1bd3e..$1d9e8, mvars = module bytes 12288..$35bc.
A relative <out.json> is written under scratchpad/captive/agents/mapgen/.
"""
import json
import os
import sys


def root():
    d = os.environ.get('M68000_ROOT') or os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(d, 'tools', 'rdis.py')):
        p = os.path.dirname(d)
        if p == d:
            sys.exit('repo root (tools/rdis.py) not found')
        d = p
    return d


R = root()
sys.path.insert(0, os.path.join(R, 'tools'))
from stclient import StServer  # noqa: E402

W = os.path.join(R, 'scratchpad', 'captive')
OUT = os.path.join(W, 'agents', 'mapgen')
SNAP = os.path.join(W, 'mg_ret.snap')
MA6 = 0x20376
ENTRY = 0x20054
POISON = os.environ.get('MAPGEN_POISON') == '1'
RET = 0xFD0000  # in the TOS ROM: an address the module never reaches
REGIONS = {'g0': (MA6 + 56, 4096), 'g1': (MA6 + 4168, 4096), 'g2': (MA6 + 8280, 4096),
           'outa': (0x1d9e8, 2048), 'outb': (0x1e208, 2048), 'vars': (MA6, 56),
           'fedtab': (0x1bd3e, 0x1d9e8 - 0x1bd3e), 'mvars': (MA6 + 12288, 0x35bc - 12288)}


def outpath(p):
    """A bare or relative path goes under OUT."""
    if os.path.isabs(p):
        return p
    os.makedirs(OUT, exist_ok=True)
    return os.path.join(OUT, p)


def start(s, d0, d1, d2, d3, stops=(), max_steps=60_000_000):
    """Load mg_ret.snap and call the body with the given arguments, optionally stopping early at `stops`."""
    s('load', snapshot=SNAP)
    s.sp = None
    if POISON:
        for k in ('g0', 'g1', 'g2', 'outa', 'outb'):
            a, n = REGIONS[k]
            for i in range(0, n, 4):
                s('poke', addr=a + i, width=4, value=0x5A5A5A5A)
    return s.call(ENTRY, ret=RET, max_steps=max_steps, stops=list(stops), d0=d0, d1=d1, d2=d2, d3=d3,
                  d4=0xFFFFFFFF, a0=0x1d9e8, a1=0xb532, a2=0x303c)


def run_case(s, d0, d1, d2, d3):
    r = start(s, d0, d1, d2, d3)
    regs = s('regs')
    out = {'args': [d0, d1, d2, d3], 'steps': r['steps'], 'regs': {k: regs[k] for k in
           ['d0', 'd1', 'd2', 'd3', 'd4', 'd5', 'd6', 'd7', 'a0', 'a1', 'a2']}}
    for k, (a, n) in REGIONS.items():
        out[k] = s.read(a, n).hex()
    return out


def run_cases(cases):
    s = StServer(R)
    res = []
    try:
        for c in cases:
            o = run_case(s, *c)
            print(c, o['steps'], o['regs']['d0'], o['regs']['d5'], o['regs']['d6'], flush=True)
            res.append(o)
    finally:
        s.close()
    return res


def grids(o):
    """Decoded per-cell lists (index y*64+x) of one case."""
    g0 = bytes.fromhex(o['g0'])
    g1 = bytes.fromhex(o['g1'])
    g2 = bytes.fromhex(o['g2'])
    return {'g0': [int.from_bytes(g0[2 * i:2 * i + 2], 'big') for i in range(2048)],
            'feat': [g1[2 * i + 1] for i in range(2048)], 'param': [g1[2 * i] for i in range(2048)],
            'g2': [g2[2 * i] for i in range(2048)], 'vars': bytes.fromhex(o['vars']),
            'outa': bytes.fromhex(o['outa']), 'outb': bytes.fromhex(o['outb'])}


def main():
    cases = [[int(x, 0) for x in c.split(',')] for c in sys.argv[2:]]
    json.dump(run_cases(cases), open(outpath(sys.argv[1]), 'w'))


if __name__ == '__main__':
    main()
