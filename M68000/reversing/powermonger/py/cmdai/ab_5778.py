"""A/B of the `$5778` overwrite of the group's opponent-class word (record +280, group view +204).

For each start snapshot and group (side s, group k) whose state is $d and whose +204 holds an entity offset (the `$57e6`
write), two runs of the same budget: A unpoked, B with the word put back to 4 (`w` writes a longword: the following word,
group k+1's +204, is read from the snapshot and written back unchanged). Each run counts the AI decision points that read
the word (`$65ec` escort test, `$65f4` escort issued, `$6726` posture test, `$672e` posture := 2) and a few combat/AI
routines, then snapshots; the two end states are compared byte for byte and the group's fields printed.

Reverse A/B: a case `snap:s:k:val` takes a group whose word holds a class (4, group 0 fighting a group) and B writes `val`
(hex, an entity offset, as `$57e6` would): the escort arm `$65ec` of the side's other groups then sees no class 4.

Usage: python3 ab_5778.py [steps] [snap:s:k[:val] ...]   (default: the natural cases listed in CASES, 20M steps)
Output under $PM_WORK (default scratchpad/pmwork)/ab/.
"""
import os
import struct
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path


def root():
    for d in Path(__file__).resolve().parents:
        if (d / "tools" / "rdis.py").exists():
            return d
    sys.exit("repo root not found")


ROOT = Path(os.environ.get("M68000_ROOT", root()))
WORK = ROOT / os.environ.get("PM_WORK", "scratchpad/pmwork") / "ab"
WORK.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(ROOT / "tools"))
from gfxview import load_ram  # noqa: E402

GROUPS = 0x51538
HITS = "6526 66e8 6726 672e 6734 673e 65ec 65f4 65c8 6638 664c 666c 668c 66a4 6822 5590 5778 57e6 4bc8 4d70 3728 6762"
CASES = ["scratchpad/pm148/arms/long/L2G_k76_c1.snap:4:0", "scratchpad/pm148/arms/long/L2G_k44_c1.snap:4:0",
         "scratchpad/pm143/run/p0k60_s3.snap:4:0", "scratchpad/pm148/arms/long/L2G_k25_c2.snap:2:0",
         "scratchpad/pm148/arms/long/M2G_k126_c1.snap:2:0", "scratchpad/pm148/arms/long/L2G_k8_c1.snap:2:1",
         "scratchpad/pm148/arms/long/M2G_k14_c1.snap:2:1", "scratchpad/pm148/arms/long/M2G_k110_c1.snap:4:1"]
w = lambda r, a: struct.unpack_from(">h", r, a)[0]


def group_line(r, s, k):
    a = GROUPS + 316 * s + 2 * k          # record view: owner +28, men +52, state +76, posture +136, class +280, opponent +292
    return (f"state {w(r, a + 76)} men {w(r, a + 52)} posture {w(r, a + 136)} +280 {w(r, a + 280)} +292 {w(r, a + 292)} "
            f"link {w(r, a + 4)} food {w(r, a + 112)}")


def run(name, snap, pokes, steps):
    cmds = ["disk scratchpad/powermonger.st"] + pokes + [f"hits {steps} {HITS}", f"snap {WORK.relative_to(ROOT)}/{name}.snap", "q"]
    p = subprocess.run(["dotnet", "exec", "bin/Debug/net8.0/M68000.dll", "resume", snap, "repl"], input="\n".join(cmds) + "\n",
                       capture_output=True, text=True, cwd=ROOT, env=dict(os.environ, ATARI_NOTRACE="1"))
    (WORK / f"{name}.out").write_text(p.stdout + p.stderr)
    hits = {}
    for line in (p.stdout + p.stderr).splitlines():
        t = line.split()
        if len(t) >= 2 and t[0].startswith("$0") and t[1].isdigit():
            hits[t[0][1:].lstrip("0")] = int(t[1])
    return hits


def main():
    args = sys.argv[1:]
    steps = int(args.pop(0)) if args and args[0].isdigit() else 20_000_000
    for case in args or CASES:
        parts = case.split(":")
        val = int(parts.pop(), 16) if len(parts) == 4 else 4
        snap, s, k = parts[0], int(parts[1]), int(parts[2])
        r, _ = load_ram(str(ROOT / snap))
        a = GROUPS + 316 * s + 2 * k + 280
        cur, nxt = w(r, a), struct.unpack_from(">H", r, a + 2)[0]
        tag = f"{Path(snap).stem}_s{s}k{k}"
        print(f"== {tag}: start {group_line(r, s, k)}")
        if w(r, a - 280 + 76) != 13 or (val == 4) == (cur in (0, 2, 4, 6, 8, 10, 12)):
            print("   not a state-$d group with an offset (or, reverse, a class) in +280: skipped")
            continue
        poke = f"w {a:x} {(val << 16) | nxt:08x}"
        with ThreadPoolExecutor(2) as ex:
            fa = ex.submit(run, f"{tag}_A", snap, [], steps)
            fb = ex.submit(run, f"{tag}_B", snap, [poke], steps)
            ha, hb = fa.result(), fb.result()
        ra, _ = load_ram(str(WORK / f"{tag}_A.snap"))
        rb, _ = load_ram(str(WORK / f"{tag}_B.snap"))
        diff = sum(1 for i in range(len(ra)) if ra[i] != rb[i])
        print(f"   B poke: {poke} (was {cur})")
        print("   hits  " + " ".join(f"{h}:{ha.get(h, '?')}/{hb.get(h, '?')}" for h in HITS.split()) + "   (A/B)")
        print(f"   end A {group_line(ra, s, k)}")
        print(f"   end B {group_line(rb, s, k)}")
        print(f"   RAM bytes differing at the end: {diff}")


if __name__ == "__main__":
    main()
