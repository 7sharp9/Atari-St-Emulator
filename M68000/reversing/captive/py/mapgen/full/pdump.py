"""Stage dumps like stages/dumpall.py, for any list of D0 values, written under scratchpad/captive/mapgen_full/pdumps/.

    uv run python -I reversing/captive/py/mapgen/full/pdump.py <d2> <d0> [<d0> ...]

Writes d<d2>_<d0>.bin under scratchpad/captive/mapgen_full/pdumps/ (same record format as dumpall.py).
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pmodels  # noqa: E402,F401  (puts stages/ on the path)
from common import FED, FLEN, MLEN, R, STOPS  # noqa: E402

sys.path.insert(0, os.path.join(R, 'reversing', 'captive', 'py', 'mapgen'))
from gen import MA6, RET, start  # noqa: E402
from stclient import StServer  # noqa: E402

OUT = os.path.join(R, 'scratchpad', 'captive', 'mapgen_full', 'pdumps')


def main():
    d2 = int(sys.argv[1])
    os.makedirs(OUT, exist_ok=True)
    s = StServer(R)
    try:
        for d0 in [int(a, 0) for a in sys.argv[2:]]:
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
            open(os.path.join(OUT, f'd{d2}_{d0}.bin'), 'wb').write(out)
            print(d2, d0, n, 'stops', flush=True)
    finally:
        s.close()


if __name__ == '__main__':
    main()
