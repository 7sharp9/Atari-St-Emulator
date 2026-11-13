"""Capture fed_MapGen's state before and after the encoder $23936 and at the call's return, for many bases.

    uv run python -I reversing/captive/py/mapgen/full/capture_final.py <out.bin> <d2> <lo> <hi>

Each case is mapgen/gen.py's labelled-poke call of $20054 from mg_ret.snap with D0 = seed, D1 = 0, D2 = d2, D3 = 0.
It stops at $200ee (bsr $23936), $200f2 (its return) and the planted return address, and reads at each the module
block A6 = $20376 .. +$35bc and federation $1bd3e .. $1ea08 (tables, then tile layer $1d9e8 and plane 2 $1e208);
at the return also D0, D5, D6. Record: <HH> (seed, d2), 3 x (module, fed), then 3 longs.
A relative <out.bin> goes under scratchpad/captive/mapgen_full/final/.
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
R = HERE
while not os.path.exists(os.path.join(R, 'tools', 'rdis.py')):
    R = os.path.dirname(R)
sys.path.insert(0, os.path.join(R, 'reversing', 'captive', 'py', 'mapgen'))
sys.path.insert(0, os.path.join(R, 'tools'))
from gen import MA6, RET, start  # noqa: E402
from stclient import StServer  # noqa: E402

MLEN = 0x35bc
FED, FEND = 0x1bd3e, 0x1ea08
REC = 4 + 3 * (MLEN + FEND - FED) + 12


def main():
    out, d2, lo, hi = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])
    if not os.path.isabs(out):
        os.makedirs(os.path.join(R, 'scratchpad', 'captive', 'mapgen_full', 'final'), exist_ok=True)
        out = os.path.join(R, 'scratchpad', 'captive', 'mapgen_full', 'final', out)
    s = StServer(R)
    buf = bytearray()
    try:
        for d0 in range(lo, hi):
            start(s, d0, 0, d2, 0, stops=[0x200ee])
            rec = struct.pack('>HH', d0, d2)
            for nxt in (0x200f2, RET, None):
                assert s.reg('pc') in (0x200ee, 0x200f2, RET), hex(s.reg('pc'))
                rec += s.read(MA6, MLEN) + s.read(FED, FEND - FED)
                if nxt is None:
                    break
                r = s('run', max_steps=60_000_000, until_pc=[nxt])
                if r['reason'] != 'until':
                    sys.exit(f'stopped: {r}')
            rec += struct.pack('>III', *(s.reg(k) & 0xffffffff for k in ('d0', 'd5', 'd6')))
            assert len(rec) == REC
            buf += rec
            print(d2, d0, flush=True)
    finally:
        s.close()
    open(out, 'wb').write(buf)


if __name__ == '__main__':
    main()
