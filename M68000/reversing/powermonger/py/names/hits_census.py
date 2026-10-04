"""hits_census.py <snap> <steps> <hexaddr>...: `hits` over <steps> real steps from a snapshot (no pokes), one line per address.
Run from M68000/ (the emulator needs the cwd).  Output also saved under $PM_WORK/names/ (default scratchpad/pmwork/names)/hits_<snap>_<steps>.txt."""
import os, re, subprocess, sys
from pathlib import Path
ROOT = Path(os.environ.get("M68000_ROOT", Path(__file__).resolve().parents[4]))
snap, steps, addrs = sys.argv[1], int(sys.argv[2]), sys.argv[3:]
argv = ["dotnet", "exec", "bin/Debug/net8.0/M68000.dll", "resume", snap, "repl", "--disk-a", "scratchpad/powermonger.st"]
cmds = "hits %d %s\nq\n" % (steps, " ".join(addrs))
p = subprocess.run(argv, input=cmds, capture_output=True, text=True, cwd=ROOT, timeout=3000, env=dict(os.environ, ATARI_NOTRACE="1"))
out = p.stdout + p.stderr
d = (ROOT / os.environ.get("PM_WORK", "scratchpad/pmwork")) / "names"
d.mkdir(parents=True, exist_ok=True)
(d / ("hits_%s_%d.txt" % (Path(snap).stem, steps))).write_text(out)
print("==", snap, steps)
for l in out.splitlines():
    if re.search(r"\$[0-9a-f]{6,8}\s+\d+\s+first", l):
        print(l.strip())
