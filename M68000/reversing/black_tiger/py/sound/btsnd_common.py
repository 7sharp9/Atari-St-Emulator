"""Shared helpers for the Black Tiger sound decoder (snapshot reader, paths).

Repo root from __file__ (M68000_ROOT overrides); inputs from $BT_WORK (default
M68000/scratchpad/black_tiger); outputs under $BT_WORK/agents/sound/.
"""
import os
import struct

HERE = os.path.dirname(os.path.abspath(__file__))


def _find_root():
    d = HERE
    while d != os.path.dirname(d):
        if os.path.exists(os.path.join(d, "M68000.fsproj")):
            return d
        d = os.path.dirname(d)
    raise SystemExit("M68000 root not found; set M68000_ROOT")


ROOT = os.environ.get("M68000_ROOT") or _find_root()
BT_WORK = os.environ.get("BT_WORK") or os.path.join(ROOT, "scratchpad", "black_tiger")
OUT = os.path.join(BT_WORK, "agents", "sound")
FILES = os.path.join(BT_WORK, "files")


class Snap:
    """Minimal .snap (format v11) reader: regs, RAM, YM2149 register file."""

    def __init__(self, path):
        d = open(path, "rb").read()
        assert d[:4] == b"A68S", path
        self.ver = d[4]
        n = 19 if self.ver >= 5 else 18
        vals = struct.unpack_from("<%di" % n, d, 5)
        names = ["d%d" % i for i in range(8)] + ["a%d" % i for i in range(8)] + ["usp", "ssp", "pc"]
        self.regs = {k: v & 0xFFFFFFFF for k, v in zip(names, vals)}
        off = 5 + n * 4 + 2
        arrs = []
        for _ in range(4):  # ram, video, ym2149, mfp
            ln = struct.unpack_from("<i", d, off)[0]
            off += 4
            arrs.append(d[off:off + ln])
            off += ln
        self.ram, self.video, self.ym, self.mfp = arrs

    def b(self, a):
        return self.ram[a]

    def w(self, a):
        return int.from_bytes(self.ram[a:a + 2], "big")

    def l(self, a):
        return int.from_bytes(self.ram[a:a + 4], "big")
