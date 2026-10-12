"""Live season slots ([$ff9e]+3712, 2304 bytes) vs the current season's source ($1aba2[$57fd0]):
pixels that differ, and whether pixel 0 (x = 0, the LCG value that wraps instead of copying) differs.

    cd M68000 && uv run python <this> <ram-or-snap>...
"""
import struct
import sys
from pathlib import Path

ROOT = next(p for p in Path(__file__).resolve().parents if (p / "tools" / "rdis.py").exists())
sys.path.insert(0, str(ROOT / "tools"))
from disassemble import ram_from_snap  # noqa: E402


def pix(m, base, x):
    g, b = x >> 4, x & 15
    v = 0
    for p in range(4):
        w = struct.unpack_from(">H", m, base + g * 8 + p * 2)[0]
        v |= ((w >> b) & 1) << p
    return v


for f in sys.argv[1:]:
    m = ram_from_snap(f) if f.endswith(".snap") else open(f, "rb").read()
    w = lambda a: struct.unpack_from(">H", m, a)[0]  # noqa: E731
    base = struct.unpack_from(">I", m, 0xff9e)[0]
    fd0, fec = w(0x57fd0), w(0x57fec)
    live = base + 3712
    srcs = {s: base + w(0x1aba2 + s) for s in (0, 2, 4, 6)}
    cur = srcs[fd0]
    diff = [x for x in range(4608) if pix(m, live, x) != pix(m, cur, x)]
    p0 = {s: pix(m, a, 0) for s, a in srcs.items()}
    print(f"{f}: season {fd0} count {fec}: {len(diff)} of 4608 pixels differ from the current source; "
          f"pixel 0 live {pix(m, live, 0)}, sources {p0}; first diffs {diff[:6]}")
