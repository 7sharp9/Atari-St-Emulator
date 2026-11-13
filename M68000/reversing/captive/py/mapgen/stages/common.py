"""Shared paths, stage list, dump reader and 68000-style memory helpers for the stage models."""
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
AGENT = os.path.join(R, 'scratchpad', 'captive', 'mapgen_stages')   # output (gitignored)
DUMPS = os.path.join(AGENT, 'dumps')
MLEN = 0x35bc            # module variables at A6 = $20376
FED = 0x1bd3e            # federation table block the A1 pointers address
FLEN = 0x1d9e8 - FED
REC = 4 + MLEN + FLEN

# (stop pc = return address of the bsr, callee). First entry: the base path's first bsr ($23c82, before $2624a).
STAGES = [(0x23c82, None), (0x23c86, 0x2624a), (0x23c8a, 0x2011e), (0x23c8e, 0x201de), (0x23c92, 0x202a2),
          (0x23ca8, 0x245e2), (0x23cb0, 0x263c2), (0x23cb4, 0x244b6), (0x23cb8, 0x24d78), (0x23cbc, 0x24f4c),
          (0x23cc0, 0x25198), (0x23cc4, 0x2533a), (0x23cc8, 0x25198), (0x23ccc, 0x25162), (0x23cd0, 0x263fa),
          (0x23cd4, 0x25240), (0x23cea, 0x2676c), (0x23cee, 0x25c1e), (0x23cf2, 0x256f0), (0x23cf6, 0x25722),
          (0x23cfa, 0x25414), (0x23cfe, 0x2543a), (0x23d02, 0x2419a), (0x23d0a, 0x24d64), (0x23d0e, 0x24128),
          (0x23d12, 0x240c2), (0x23d16, 0x25d88), (0x23d1a, 0x26438), (0x23d1e, 0x26478), (0x23d22, 0x264ac),
          (0x23d26, 0x264c8), (0x23d2a, 0x265cc), (0x23d2e, 0x26606), (0x23d36, 0x24d64), (0x23d3a, 0x2630c),
          (0x23d3e, 0x26854), (0x23d42, 0x26532), (0x23d46, 0x26570), (0x23d4a, 0x268f8)]
STOPS = [a for a, _ in STAGES]

G0, G1, G2 = 56, 4168, 8280      # module offsets of the three grids


def load(d2, d0):
    """List of (stop pc, module bytearray, federation bytearray), one per stop in STAGES order."""
    b = open(os.path.join(DUMPS, f'd{d2}_{d0}.bin'), 'rb').read()
    out = []
    for i in range(0, len(b), REC):
        out.append((int.from_bytes(b[i:i + 4], 'big'), bytearray(b[i + 4:i + 4 + MLEN]),
                    bytearray(b[i + 4 + MLEN:i + REC])))
    return out


def before_after(d2, d0, callee_stop):
    """(module, fed) before and after the stage whose return address is callee_stop."""
    recs = load(d2, d0)
    i = [r[0] for r in recs].index(callee_stop)
    return recs[i - 1], recs[i]


class M:
    """Big-endian word/byte access to the module variable block (offsets from A6)."""

    def __init__(self, b, fed=None):
        self.b = b
        self.fed = fed

    def w(self, o):
        return (self.b[o] << 8) | self.b[o + 1]

    def sw(self, o):
        v = self.w(o)
        return v - 0x10000 if v & 0x8000 else v

    def setw(self, o, v):
        v &= 0xffff
        self.b[o], self.b[o + 1] = v >> 8, v & 0xff

    def l(self, o):
        return int.from_bytes(self.b[o:o + 4], 'big')

    # RNG $23b96: seed = seed * $5e5 + $29; returns ror.w #4 of it, eor $800
    def rng(self):
        x = (self.w(12404) * 0x5e5 + 0x29) & 0xffff
        self.setw(12404, x)
        return (((x >> 4) | (x << 12)) & 0xffff) ^ 0x800

    # G0 word, G1 byte pair, by cell offset D5 = 2 * (64 y + x)
    def g0(self, d5):
        return self.w(G0 + d5)

    def setg0(self, d5, v):
        self.setw(G0 + d5, v)


def ror(v, n, bits=16):
    m = (1 << bits) - 1
    v &= m
    return ((v >> n) | (v << (bits - n))) & m


def rol(v, n, bits=16):
    return ror(v, bits - n, bits)


def diffs(a, b, lo=0, hi=None):
    hi = hi or len(a)
    return [i for i in range(lo, hi) if a[i] != b[i]]
