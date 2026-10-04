"""rerank_follow.py <snap> <n> [steps...]: stop at the n-th natural `$1d70` (_rerank) entry from <snap>, run to its rts ($1e8a), then follow the men whose mode changed
at the rts (all set to mode $08, prev $08, offsets 20/22) over the given step counts (default 2000 10000 40000 150000): histogram of their modes, how many
are at their orbit slot (lead position + rotated (20,22) offset within 2 cells), and how many hold the lead's step (12) after reaching it. Run from M68000/."""
import os, subprocess, sys
from collections import Counter
from pathlib import Path
ROOT = Path(os.environ.get("M68000_ROOT", Path(__file__).resolve().parents[4]))
sys.path.insert(0, str(ROOT / "tools"))
from disassemble import ram_from_snap
OBJ = 0x51b66
snap, n = sys.argv[1], int(sys.argv[2])
steps = [int(x) for x in sys.argv[3:]] or [2000, 10000, 40000, 150000]
out = (ROOT / os.environ.get("PM_WORK", "scratchpad/pmwork")) / "names" / ("rf_%s_%d" % (Path(snap).stem, n)); (ROOT / out).mkdir(parents=True, exist_ok=True)
cmds = ["bpc 1d70 %d 200000000" % n, "snap %s/entry.snap" % out, "bp 1e8a 300000", "snap %s/rts.snap" % out]
prev = 0
for s in steps:
    cmds += ["s %d" % (s - prev), "snap %s/t%d.snap" % (out, s)]; prev = s
cmds.append("q")
argv = ["dotnet", "exec", "bin/Debug/net8.0/M68000.dll", "resume", snap, "repl", "--disk-a", "scratchpad/powermonger.st"]
subprocess.run(argv, input="\n".join(cmds) + "\n", capture_output=True, text=True, cwd=ROOT, timeout=3000, env=dict(os.environ, ATARI_NOTRACE="1"))
e = ram_from_snap(ROOT / out / "entry.snap"); x = ram_from_snap(ROOT / out / "rts.snap")
men = [i for i in range(512) if e[OBJ + 50 * i + 31] != x[OBJ + 50 * i + 31] and x[OBJ + 50 * i + 31] == 8]
print("men re-moded to $08 by the rerank:", len(men), "old modes", Counter("%02x" % e[OBJ + 50 * i + 31] for i in men))
for s in steps:
    t = ram_from_snap(ROOT / out / ("t%d.snap" % s))
    print("after +%6d steps: modes %s" % (s, dict(Counter("%02x" % t[OBJ + 50 * i + 31] for i in men))))
