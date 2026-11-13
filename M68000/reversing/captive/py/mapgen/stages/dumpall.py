"""Dump fed_MapGen's whole state at every stage boundary of $23bb0's base path, for many seeds.

    uv run python -I reversing/captive/py/mapgen/stages/dumpall.py <d2> <lo> <hi>

For D0 = lo..hi-1 (D1 = $ffff, D3 = 0) through gen.py's shortcut call (labelled register pokes, see gen.py), stop at
the return address of every `bsr` of the base path (stagedump.STAGES, plus the entry of the first stage, $23c82) and
read the module's variables 0..$35bc from A6 = $20376 and federation's table block $1bd3e..$1d9e8. Writes
dumps/d<d2>_<d0>.bin under scratchpad/captive/mapgen_stages/: per stop a 4-byte stop PC, then MLEN module bytes, then FLEN
federation bytes. For D2 = 0 the stop at $23cea is reached without $2676c having run (its record repeats the last).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import FED, FLEN, MLEN, R, DUMPS, STOPS  # noqa: E402

sys.path.insert(0, os.path.join(R, 'reversing', 'captive', 'py', 'mapgen'))
from gen import MA6, RET, start  # noqa: E402
from stclient import StServer  # noqa: E402


def main():
    d2, lo, hi = int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3])
    os.makedirs(DUMPS, exist_ok=True)
    s = StServer(R)
    try:
        for d0 in range(lo, hi):
            start(s, d0, 0xffff, d2, 0, stops=STOPS)
            out = bytearray()
            n = 0
            while True:
                pc = s.reg('pc')
                if pc == RET:
                    break
                out += pc.to_bytes(4, 'big') + s.read(MA6, MLEN) + s.read(FED, FLEN)
                n += 1
                r = s('run', max_steps=60_000_000, until_pc=[RET] + STOPS)
                if r['reason'] != 'until':
                    sys.exit(f'stopped: {r}')
            open(os.path.join(DUMPS, f'd{d2}_{d0}.bin'), 'wb').write(out)
            print(d2, d0, n, 'stops', flush=True)
    finally:
        s.close()


if __name__ == '__main__':
    main()
