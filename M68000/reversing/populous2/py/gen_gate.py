"""Populous II world generator gen_land $1ebee: callcap against a literal model, byte for byte.

Model (read from $1ebee, $1ec38, $1ec8c, $215dc):
  gen_land: clear the 64x64 cell map ($3979e, 4 bytes per cell). For each 4-word record of the hill
    table $30664 (y range, y base, x range, x base; ended by $ff9d):
      r1 = rand(); y = r1 mod yrange + ybase;  r2 = rand(); x = r2 mod xrange + xbase
      hill_walk(x, y, s6 = r1, s7 = r2)
  hill_walk: repeat
      s6 = (s6 * $24a1 + $24df) & $7fff;  x += s6 mod 7 - 3
      s7 = (s7 * $24a1 + $24df) & $7fff;  y += s7 mod 7 - 3
      raise_point(x, y)
    until raise_point rejected the corner (outside 0..64, or already at 8) or raised it to 8.
  raise_point: as in raise_gate.py (neighbours N, NE, E, SE, S, SW, W, NW; recurse into each lower
    one; then write), with the write done as the code does it on the four cells sharing the corner:
    cell (x-1,y-1) bit 4, (x,y-1) bit 8, (x-1,y) bit 2, (x,y) bit 1 of the corner mask
    m = $36b7a[b1]: if the bit is clear, b1 = m + bit; else b0 += 1 and b1 = m & ($f0 | bit);
    then b0 &= 7. Counts: $39788 += 1 per call, $3962c += 1 per corner raised.
  rand: seed = seed * $bb40e62d mod 2^32 (0 replaced by $bc614e first), result (seed >> 8) & $7fff.

Each case pokes the seed long $47382 and callcaps $1ebee from a snapshot stopped at its entry.
Compared: all $4000 bytes of the cell map, the final seed, $39788 and $3962c.
Controls: the walk's stop rule changed to Populous 1's height 6; the corner written before the
recursion, as Populous 1's raise_point does (same neighbour test, h+1 - n > 1).

usage: uv run python reversing/populous2/py/gen_gate.py <entry snap> [n]
"""
import json
import os
import random
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from corners import ROOT  # noqa: E402

sys.path.insert(0, os.path.join(ROOT, "tools"))
from gfxview import load_ram  # noqa: E402

CELLS = 0x3979E
ORDER = ((0, -1), (1, -1), (1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1))


def w16(ram, a):
    return (ram[a] << 8) | ram[a + 1]


class Gen:
    def __init__(self, ram, seed, stop=8, write_first=False):
        self.write_first = write_first
        self.T = ram[0x36B7A:0x36B7A + 256]
        self.table = [w16(ram, 0x30664 + 2 * i) for i in range(64)]
        self.seed = seed
        self.stop = stop
        self.b = bytearray(0x4000)
        self.calls = w16(ram, 0x39788)
        self.count = w16(ram, 0x3962C)

    def rand(self):
        if self.seed == 0:
            self.seed = 0xBC614E
        self.seed = (self.seed * 0xBB40E62D) & 0xFFFFFFFF
        return (self.seed >> 8) & 0x7FFF

    def corner(self, x, y):
        if not (0 <= x <= 64 and 0 <= y <= 64):
            return None
        for cx, cy, k in ((x, y, 0), (x - 1, y, 1), (x - 1, y - 1, 2), (x, y - 1, 3)):
            if 0 <= cx < 64 and 0 <= cy < 64:
                o = (cy * 64 + cx) * 4
                return (self.b[o] & 7) + ((self.T[self.b[o + 1]] >> k) & 1)

    def write(self, x, y):
        for cx, cy, bit in ((x - 1, y - 1, 4), (x, y - 1, 8), (x - 1, y, 2), (x, y, 1)):
            if 0 <= cx < 64 and 0 <= cy < 64:
                o = (cy * 64 + cx) * 4
                m = self.T[self.b[o + 1]]
                if m & bit:
                    self.b[o] = (self.b[o] + 1) & 0xFF
                    m &= 0xF0 | bit
                else:
                    m = (m + bit) & 0xFF
                self.b[o + 1] = m
                self.b[o] &= 7

    def raise_point(self, x, y):
        self.calls = (self.calls + 1) & 0xFFFF
        h = self.corner(x, y)
        if h is None or h == 8:
            return -1
        if self.write_first:
            self.write(x, y)
        for dx, dy in ORDER:
            n = self.corner(x + dx, y + dy)
            if n is not None and n < (h + 1 if self.write_first else h) - (1 if self.write_first else 0):
                self.raise_point(x + dx, y + dy)
        if not self.write_first:
            self.write(x, y)
        self.count = (self.count + 1) & 0xFFFF
        return h + 1

    def run(self):
        i = 0
        while True:
            yr, yb, xr, xb = self.table[i:i + 4]
            if yr == 0xFF9D:
                break
            i += 4
            r1 = self.rand()
            y = r1 % yr + yb
            r2 = self.rand()
            x = r2 % xr + xb
            s6, s7 = r1, r2
            while True:
                s6 = (s6 * 0x24A1 + 0x24DF) & 0x7FFF
                x += s6 % 7 - 3
                s7 = (s7 * 0x24A1 + 0x24DF) & 0x7FFF
                y += s7 % 7 - 3
                h = self.raise_point(x, y)
                if h < 0 or h >= self.stop:
                    break
        return self


def main():
    snap = sys.argv[1]
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 30
    ram0, _ = load_ram(snap)
    assert ram0[0x30664:0x30666] != b"\xff\x9d", "empty hill table"
    random.seed(11)
    seed0 = int.from_bytes(ram0[0x47382:0x47386], "big")
    seeds = [seed0, 0, 1, 0xFFFFFFFF] + [random.getrandbits(32) for _ in range(n - 4)]
    out = "scratchpad/populous2/genland/gate"
    os.makedirs(os.path.join(ROOT, out), exist_ok=True)
    script = "".join(f"w 47382 {s:08x}\ncallcap 1ebee 20000000 {out}/s{i}.json\n" for i, s in enumerate(seeds))
    dll = os.path.join(ROOT, "bin", "Debug", "net8.0", "M68000.dll")
    r = subprocess.run(["dotnet", "exec", dll, "resume", snap, "repl"], input=script + "q\n",
                       capture_output=True, text=True, cwd=ROOT)
    got = r.stdout.count("--- callcap $01ebee: returned")
    if got != len(seeds):
        sys.exit(f"expected {len(seeds)} returned callcaps, got {got}\n{r.stdout[-1500:]}{r.stderr[-800:]}")
    cells_ok = full_ok = ctl_ok = wf_ok = 0
    land = []
    for i, s in enumerate(seeds):
        cap = json.load(open(os.path.join(ROOT, out, f"s{i}.json")))
        ram = bytearray(ram0)
        for a in range(0x47382, 0x47386):
            ram[a] = 0
        ram[0x47382:0x47386] = s.to_bytes(4, "big")
        for a, _old, new in cap["mem"]:
            ram[a] = new
        g = Gen(ram0, s).run()
        c = Gen(ram0, s, stop=6).run()
        wf = Gen(ram0, s, write_first=True).run()
        emu = bytes(ram[CELLS:CELLS + 0x4000])
        same = emu == bytes(g.b)
        cells_ok += same
        ctl_ok += emu == bytes(c.b)
        wf_ok += emu == bytes(wf.b)
        full_ok += (same and int.from_bytes(ram[0x47382:0x47386], "big") == g.seed
                    and w16(ram, 0x39788) == g.calls and w16(ram, 0x3962C) == g.count)
        land.append(sum(1 for k in range(4096) if emu[4 * k] & 7 or emu[4 * k + 1]))
        if not same:
            diff = [k for k in range(0x4000) if emu[k] != g.b[k]]
            print(f"seed {s:08x}: {len(diff)} bytes differ, first cells {[(k // 4 % 64, k // 256, k % 4) for k in diff[:6]]}")
    print(f"seeds {len(seeds)}: cell map ($4000 bytes) equal to the model {cells_ok}/{len(seeds)}; "
          f"with final seed, $39788 and $3962c {full_ok}/{len(seeds)}; "
          f"controls: stop at height 6 {ctl_ok}/{len(seeds)}, corner written before the recursion {wf_ok}/{len(seeds)}")
    print(f"non-sea cells per world: min {min(land)} max {max(land)}")


if __name__ == "__main__":
    main()
