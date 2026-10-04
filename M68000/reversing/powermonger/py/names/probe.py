"""probe.py <snap> <entry hex> <exit hex> <k,...> [--dir NAME]: stop at the k-th (cumulative, from the snapshot) entry of a routine, snapshot,
run on to its exit address (rts), snapshot; then print what changed in the group table ($51538 states), the side blocks ($580a6 +6 peace bits),
and the 50-byte object records that differ, with the entry registers.  Run from M68000/.  Used for `$4bc8` (`$4d70` -> state $d), `$37c2`, `$5778`."""
import os, re, subprocess, sys
from pathlib import Path
ROOT = Path(os.environ.get("M68000_ROOT", Path(__file__).resolve().parents[4]))
sys.path.insert(0, str(ROOT / "tools"))
from disassemble import ram_from_snap
snap, entry, exit_, ks = sys.argv[1], sys.argv[2], sys.argv[3], [int(x) for x in sys.argv[4].split(",")]
name = (sys.argv[sys.argv.index("--dir") + 1] if "--dir" in sys.argv else Path(snap).stem + "_" + entry)
out = (ROOT / os.environ.get("PM_WORK", "scratchpad/pmwork")) / "names" / name
(ROOT / out).mkdir(parents=True, exist_ok=True)
cmds, prev = [], 0
for k in ks:
    cmds += ["bpc %s %d 80000000" % (entry, k - prev), "r", "snap %s/e%d.snap" % (out, k), "bp %s 200000" % exit_, "snap %s/x%d.snap" % (out, k)]
    prev = k  # the exit stop is not a hit of the entry, so counting resumes from here
cmds.append("q")
argv = ["dotnet", "exec", "bin/Debug/net8.0/M68000.dll", "resume", snap, "repl", "--disk-a", "scratchpad/powermonger.st"]
log = subprocess.run(argv, input="\n".join(cmds) + "\n", capture_output=True, text=True, cwd=ROOT, timeout=3000, env=dict(os.environ, ATARI_NOTRACE="1"))
(ROOT / out / "log.txt").write_text(log.stdout + log.stderr)
regs = re.findall(r"(D0:.*\n.*\n.*\n.*)\n", log.stdout)
G, OBJ = 0x51538, 0x51b66
for i, k in enumerate(ks):
    a = ram_from_snap(ROOT / out / ("e%d.snap" % k)); b = ram_from_snap(ROOT / out / ("x%d.snap" % k))
    print("=== hit %d of $%s -> exit $%s" % (k, entry, exit_))
    r = log.stdout.split("CPU Registers")[1 + 2 * i] if len(log.stdout.split("CPU Registers")) > 1 + 2 * i else ""
    print(" ".join(x for x in r.split() if x[:2] in ("D0", "D1", "D2", "D3", "D4", "D5", "D6", "D7", "A0", "A1", "A2", "A3")))
    for s in range(5):
        for g in range(6):
            o = G + s * 0x13c + 0x4c + 4 + 2 * g - 4  # state array = record +76 (group view 0)
            o = G + s * 0x13c + 76 + 2 * g
            sa, sb = int.from_bytes(a[o:o + 2], "big"), int.from_bytes(b[o:o + 2], "big")
            if sa != sb: print("  group side %d k %d state %d -> %d" % (s, g, sa, sb))
    for s in range(1, 6):
        o = 0x580a6 + 0x20 * s + 6
        if a[o] != b[o]: print("  side %d peace bits %02x -> %02x" % (s, a[o], b[o]))
    ch = [i for i in range(512) if a[OBJ + 50 * i:OBJ + 50 * i + 50] != b[OBJ + 50 * i:OBJ + 50 * i + 50]]
    modes = {}
    for i in ch:
        ra, rb = a[OBJ + 50 * i:OBJ + 50 * i + 50], b[OBJ + 50 * i:OBJ + 50 * i + 50]
        modes[(ra[31], rb[31])] = modes.get((ra[31], rb[31]), 0) + 1
    print("  object records changed: %d; mode byte (before,after) counts: %s" % (len(ch), {("%02x" % x, "%02x" % y): n for (x, y), n in modes.items()}))
