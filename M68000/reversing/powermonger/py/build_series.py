"""Build a land (the land poke of build_land.sh), stop where the world-build population `$2984` returns, then run forward and
snapshot at a fixed interval: the time series `gate_shepherd.py` and `gate_animals.py` read (`<out>/k<k>_<NN>.snap`).

    cd M68000
    python reversing/powermonger/py/build_series.py <k> [count=30] [step=700000] [out=scratchpad/pm139/series]

The build itself takes 2.5 M steps and `$2984` 1.4 to 8.7 M more (`bpc 2a96` waits for its `rts`, 12 M cap). Deterministic: two
runs give identical snapshots. ATARI_NOTRACE is set, as every raw `dotnet exec` run here needs.
"""
import os
import subprocess
import sys
from pathlib import Path

M68 = Path(__file__).resolve().parents[3]
k = int(sys.argv[1])
count = int(sys.argv[2]) if len(sys.argv) > 2 else 30
step = int(sys.argv[3]) if len(sys.argv) > 3 else 700000
out = sys.argv[4] if len(sys.argv) > 4 else "scratchpad/pm139/series"
(M68 / out).mkdir(parents=True, exist_ok=True)
cmds = ["w 2df92 001400b1", "w 2df8e 001400b1", "w 2df96 00010001", "u 13b9a 80000000",
        f"w 580a0 {k * 0xb + 0x3fb:08x}", f"w 5809c {k * 0x96 + 0x672:04x}0000", "bpc 2a96 1 12000000"]
for i in range(count):
    cmds += [f"s {step}", f"snap {out}/k{k}_{i:02d}.snap"]
cmds.append("q")
p = subprocess.run(["dotnet", "exec", "bin/Debug/net8.0/M68000.dll", "resume", "scratchpad/pm67_ok_pre.snap", "repl",
                    "--disk-a", "scratchpad/powermonger.st"], input="\n".join(cmds) + "\n", capture_output=True, text=True,
                   cwd=M68, env=dict(os.environ, ATARI_NOTRACE="1"))
log = p.stdout + p.stderr
saved = sum(1 for l in log.splitlines() if "state saved" in l)
print(f"land {k}: {saved} of {count} snapshots in {out}")
sys.exit(0 if saved == count else 1)
