"""Capture fed_MapGen's module block at the stage boundaries around the shaft layout $245e2, the room reservations
$263c2, the digger $244b6 and the second room pass $263fa, for a range of base seeds.

    uv run python -I reversing/captive/py/mapgen/full/shafts/capture.py <out.bin> <lo> <hi> [d2]

Each case is mapgen/gen.py's labelled-poke call of $20054 from mg_ret.snap with D0 = seed, D1 = 0, D2 = d2 (default 1),
D3 = 0. It stops at each PC in STOPS in turn and reads, at each, D0-D7 and the whole module variable block
A6 = $20376 .. +$35bc. At $23ca8 (the return from $245e2) it also reads the 50 bytes at the federation pointer
13712(A6), where $245e2 copies its $18-cell list.

  $23ca4  bsr $245e2 (shafts)          $23ca8  its return (before the RNG word is restored)
  $23cb0  bsr $244b6 (after $263c2)    $23cb4  the digger's return
  $23ccc  bsr $263fa                   $23cd0  its return

Output: records <HH> (seed, d2), then per stop 8 longs (D0-D7) + block, then the 50 federation bytes.
A relative <out.bin> goes under scratchpad/captive/mapgen_full/shafts/.
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

DATA = os.path.join(R, 'scratchpad', 'captive', 'mapgen_full', 'shafts')
NVARS = 0x35bc
STOPS = [0x23ca4, 0x23ca8, 0x23cb0, 0x23cb4, 0x23ccc, 0x23cd0]
HDR = struct.Struct('>HH')
REGS = struct.Struct('>8I')
FEDN = 50
RECLEN = HDR.size + len(STOPS) * (REGS.size + NVARS) + FEDN


def regs(s):
    r = s('regs')
    return [int(str(r[f'd{i}']).lstrip('$'), 16) for i in range(8)]


def capture(s, d0, d2):
    start(s, d0, 0, d2, 0, stops=[STOPS[0]], max_steps=5_000_000)
    out = [HDR.pack(d0, d2)]
    fed = b''
    for i, pc in enumerate(STOPS):
        if i:
            r = s('run', max_steps=40_000_000, until_pc=[pc])
            if r['reason'] != 'until':
                sys.exit(f'seed {d0}: did not reach ${pc:x} ({r})')
        if s.reg('pc') != pc:
            sys.exit(f'seed {d0}: stopped at ${s.reg("pc"):x}, not ${pc:x}')
        blk = s.read(MA6, NVARS)
        out.append(REGS.pack(*regs(s)) + blk)
        if pc == 0x23ca8:
            fed = s.read(int.from_bytes(blk[13712:13716], 'big'), FEDN)
    out.append(fed)
    return b''.join(out)


def records(path):
    """Yield dicts: seed, d2, st = {pc: (regs, block)}, fed."""
    b = open(path, 'rb').read()
    for i in range(0, len(b), RECLEN):
        seed, d2 = HDR.unpack_from(b, i)
        o = i + HDR.size
        st = {}
        for pc in STOPS:
            rg = list(REGS.unpack_from(b, o))
            st[pc] = (rg, b[o + REGS.size:o + REGS.size + NVARS])
            o += REGS.size + NVARS
        yield {'seed': seed, 'd2': d2, 'st': st, 'fed': b[o:o + FEDN]}


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
