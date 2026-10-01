"""140th pass (blit): the planar sprite blitters `$122b6` (_s16_dra: 16 px wide, rows D2) and `$12326` (_s32_dra: 32 px wide as
two 16 px blocks per row, rows D2) with every clip path (`_all_16 $123ac`, `_left_16 $1241a`, `_right_1 $12460`, `_all_32 $124a8`,
`_left_32 $12576`, `_right_3 $12628`) against a pixel model, through callcap.

Calling convention (code read of `$122b6`/`$12326`, then proved here): D0.w = x of the sprite's left pixel (screen, may be
negative or > 319), D1.w = y of its top row (may be negative or > 199), D2.w = rows, A0 = screen page base (the game passes
`$2df7c`'s long), A1 = frame in the sheet: row = [mask, p0, p1, p2, p3] words (10 bytes) for 16 px; a 32 px row is two such
blocks back to back (20 bytes, left block first). A set mask bit keeps the screen pixel: new = (old & mask) | plane.
The screen is 4 interleaved planes, 160 bytes a row, 8 bytes per 16 pixel group.

    cd M68000
    .venv/bin/python reversing/powermonger/py/blit/blit_gate.py [reuse]

Expected: `matched N/N` for each of the three sheets (16x16 `$312a0`, 32x24 `$37c7c`, 32x32 `$3af1c`) and the per-variant tally.
"""
import json
import os
import random
import subprocess
import sys
from pathlib import Path

ROOT = Path(os.environ.get("M68000_ROOT", Path(__file__).resolve().parents[4]))
sys.path.insert(0, str(ROOT / "tools"))
from pm_export import ram_from_snap

HERE = Path(__file__).resolve().parent
DATA = ROOT / "scratchpad/pm140/agents/blit"      # outputs go to the gitignored scratchpad, not next to the script
DATA.mkdir(parents=True, exist_ok=True)
SNAP = "scratchpad/pm123/win/m1_s0.snap"
OUT = DATA / "gate_out"
OUT.mkdir(exist_ok=True)
ram = bytearray(ram_from_snap(ROOT / SNAP))
A0 = int.from_bytes(ram[0x2df7c:0x2df80], "big")


def w(a):
    return (ram[a] << 8) | ram[a + 1]


def model(mem, a0, a1, x, y, rows, wide):
    """Return {addr: byte} changed by drawing the sprite with clipping to 320x200."""
    out = {}
    blocks = 2 if wide else 1
    stride = 10 * blocks
    for r in range(rows):
        yy = y + r
        if not 0 <= yy < 200:
            continue
        for b in range(blocks):
            base = a1 + r * stride + b * 10
            mask = w(base)
            pl = [w(base + 2 + 2 * k) for k in range(4)]
            for i in range(16):
                xx = x + 16 * b + i
                if not 0 <= xx < 320:
                    continue
                grp, bit = xx >> 4, 15 - (xx & 15)
                for k in range(4):
                    addr = a0 + yy * 160 + grp * 8 + 2 * k
                    cur = out.get(addr)
                    if cur is None:
                        cur = (mem[addr] << 8) | mem[addr + 1]
                    m = (mask >> (15 - i)) & 1
                    p = (pl[k] >> (15 - i)) & 1
                    old = (cur >> bit) & 1
                    new = (old & m) | p
                    cur = (cur & ~(1 << bit)) | (new << bit)
                    out[addr] = cur
    res = {}
    for addr, v in out.items():
        res[addr] = v >> 8
        res[addr + 1] = v & 0xff
    return res


def variant(x, y, rows, wide):
    """Which clip routine the code takes (code read of `$122b6`/`$12326`), None when nothing is drawn."""
    if y >= 200 or y + rows <= 0:
        return None
    if not wide:
        if x <= -16 or x >= 320:
            return None
        if x < 0:
            return "_left_16"
        return "_right_1" if (x & ~15) // 2 == 152 else "_all_16"
    if x <= -32 or x >= 320:
        return None
    if x <= -16:
        return "_left_16(block1)"
    if x < 0:
        return "_left_32"
    g = (x & ~15) // 2
    return "_all_32" if g < 144 else "_right_3" if g < 152 else "_right_1(block0)" if g < 160 else None


def cases():
    rnd = random.Random(140)
    xs = [-33, -32, -31, -17, -16, -15, -9, -1, 0, 1, 7, 8, 9, 15, 16, 17, 100, 255, 271, 272, 287, 288, 289, 303, 304, 305, 319, 320, 321]
    ys = [-40, -24, -16, -1, 0, 1, 90, 167, 168, 176, 177, 183, 184, 185, 199, 200, 201]
    sheets = [("s16", 0x312a0, 160, 16, False, 0x122b6), ("s24", 0x37c7c, 480, 24, True, 0x12326),
              ("s32", 0x3af1c, 640, 32, True, 0x12326)]
    out = []
    for name, base, fsz, rows, wide, entry in sheets:
        for i in range(150):
            x = rnd.choice(xs) if i < 120 else rnd.randint(-40, 330)
            y = rnd.choice(ys) if i % 3 else rnd.randint(-40, 210)
            frame = rnd.randrange(0, 30)
            out.append((f"{name}_{i:03d}", entry, base + frame * fsz, x, y, rows, wide))
    return out


def run(cs, reuse):
    cmds = []
    for name, entry, a1, x, y, rows, wide in cs:
        f = OUT / f"o_{name}.json"
        if reuse and f.exists():
            continue
        cmds.append(f"callcap {entry:x} 200000 {f.relative_to(ROOT)} D0={x & 0xffffffff:x} D1={y & 0xffffffff:x} D2={rows:x} "
                    f"A0={A0:x} A1={a1:x}")
    if cmds:
        p = subprocess.run(["dotnet", "exec", "bin/Debug/net8.0/M68000.dll", "resume", SNAP, "repl", "--disk-a",
                            "scratchpad/powermonger.st"], input="\n".join(cmds) + "\nq\n", capture_output=True, text=True,
                           cwd=ROOT, env=dict(os.environ, ATARI_NOTRACE="1"), timeout=900)


def main():
    reuse = "reuse" in sys.argv
    cs = cases()
    run(cs, reuse)
    tot = {}
    bad = []
    for name, entry, a1, x, y, rows, wide in cs:
        f = OUT / f"o_{name}.json"
        j = json.load(open(f))
        v = variant(x, y, rows, wide)
        real = {a: after for a, before, after in j["mem"] if before != after}
        mod = model(ram, A0, a1, x, y, rows, wide)
        mod = {a: b for a, b in mod.items() if ram[a] != b}
        ok = j.get("outcome") == "returned" and real == mod
        k = (name[:3], v)
        t = tot.setdefault(k, [0, 0, 0])
        t[0] += 1
        t[1] += ok
        t[2] += len(real)
        if not ok:
            bad.append((name, x, y, v, j.get("outcome"), len(real), len(mod)))
    print("variant tally (sheet, clip routine): cases, matched, changed bytes")
    for k in sorted(tot, key=str):
        print(f"  {k[0]} {str(k[1]):18} {tot[k][0]:4d} {tot[k][1]:4d} {tot[k][2]:6d}")
    print(f"matched {sum(t[1] for t in tot.values())}/{sum(t[0] for t in tot.values())}")
    for b in bad[:20]:
        print("MISMATCH", b)


if __name__ == "__main__":
    main()
