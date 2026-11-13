"""Capture fed_MapGen's module variables just before and just after the digger $244b6 (reversing/captive/mapgen.md,
"The digger and rooms"), for a range of base seeds.

    uv run python -I <this dir>/dig_capture.py <out.bin> <lo> <hi> [d2]

Each case is mapgen/gen.py's labelled-poke call of $20054 from mg_ret.snap with D0 = seed, D1 = 0, D2 = d2 (default 1),
D3 = 0, stopped at $23cb0 (the `bsr $244b6` in $23bb0) and again at $23cb4 (its return). At both stops the whole module
variable block A6 = $20376 .. +$35bc is read (G0 56(A6), G1 4168(A6), G2 8280(A6), the RNG word 12404(A6), the room
list 12952(A6), ...), plus D0-D7 at the second stop and the steps the digger took.

Output: a binary file of records <HHI> (seed, d2, steps) + 8 longs (D0-D7 at the return) + pre block + post block.
A relative <out.bin> goes under scratchpad/captive/mapgen_digger/.
"""
import os
import struct
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
sys.path.insert(0, os.path.join(R, 'reversing', 'captive', 'py', 'mapgen'))
sys.path.insert(0, os.path.join(R, 'tools'))
from gen import MA6, start  # noqa: E402
from stclient import StServer  # noqa: E402

DATA = os.path.join(R, 'scratchpad', 'captive', 'mapgen_digger')
NVARS = 0x35bc
PRE, POST = 0x23cb0, 0x23cb4
REC = struct.Struct('>HHI8I')


def capture(s, d0, d2):
    start(s, d0, 0, d2, 0, stops=[PRE], max_steps=5_000_000)
    if s.reg('pc') != PRE:
        sys.exit(f'seed {d0}: did not stop at ${PRE:x}')
    st0 = s.reg('step')
    pre = s.read(MA6, NVARS)
    r = s('run', max_steps=40_000_000, until_pc=[POST])
    if r['reason'] != 'until':
        sys.exit(f'seed {d0}: digger did not return ({r})')
    regs = s('regs')
    dr = [int(str(regs[f'd{i}']).lstrip('$'), 16) for i in range(8)]
    post = s.read(MA6, NVARS)
    return REC.pack(d0, d2, s.reg('step') - st0, *dr) + pre + post


def records(path):
    """Yield (seed, d2, steps, [d0..d7], pre, post) from a capture file."""
    b = open(path, 'rb').read()
    n = REC.size + 2 * NVARS
    for i in range(0, len(b), n):
        h = REC.unpack_from(b, i)
        yield h[0], h[1], h[2], list(h[3:]), b[i + REC.size:i + REC.size + NVARS], b[i + REC.size + NVARS:i + n]


def main():
    out = sys.argv[1]
    if not os.path.isabs(out):
        os.makedirs(DATA, exist_ok=True)
        out = os.path.join(DATA, out)
    lo, hi = int(sys.argv[2]), int(sys.argv[3])
    d2 = int(sys.argv[4]) if len(sys.argv) > 4 else 1
    s = StServer(R)
    try:
        with open(out, 'wb') as f:
            for d0 in range(lo, hi):
                f.write(capture(s, d0, d2))
                f.flush()
    finally:
        s.close()
    print('captured', hi - lo, 'cases to', out)


if __name__ == '__main__':
    main()
