"""`callcap $1699e` (the HUD captain eyes) for every slot and frame: where does it write into the backdrop?

D0 = 2 * slot, D1 = frame; the strip pair comes from `eye_coor` ($16986).  Expected: slots 0-4 write only the row y of their
pair, inside the 16-pixel groups covering x..x+31, in about 141 steps; slot 5 (295,40) exits in 26 steps and writes nothing.

    cd M68000 && .venv/bin/python reversing/powermonger/py/fsm15/eyes_check.py [snap]
"""
import json
import os
import struct
import subprocess
import sys
from pathlib import Path

ROOT = Path(os.environ.get("M68000_ROOT", Path(__file__).resolve().parents[4]))
WORK = ROOT / "scratchpad" / "pm141" / "agents" / "fsm15" / "eyes"
snap = sys.argv[1] if len(sys.argv) > 1 else "scratchpad/pm121/run/k5_s4.snap"
sys.path.insert(0, str(ROOT / "tools"))
from pm_export import ram_from_snap

WORK.mkdir(parents=True, exist_ok=True)
rel = WORK.relative_to(ROOT).as_posix()
cmds = [f"callcap 1699e 200000 {rel}/e_{s}_{f}.json D0={s * 2:x} D1={f:x}" for s in range(6) for f in range(4)] + ["q"]
subprocess.run(["dotnet", "exec", "bin/Debug/net8.0/M68000.dll", "resume", snap, "repl", "--disk-a", "scratchpad/powermonger.st"],
               input="\n".join(cmds) + "\n", text=True, capture_output=True, cwd=ROOT, env=dict(os.environ, ATARI_NOTRACE="1"))
ram = ram_from_snap(ROOT / snap)
base = struct.unpack_from(">I", ram, 0xe0d4)[0]
coords = [struct.unpack_from(">hh", ram, 0x16986 + 4 * i) for i in range(6)]
drawn = 0
for slot in range(6):
    steps, ok = [], 0
    for fr in range(4):
        j = json.load(open(WORK / f"e_{slot}_{fr}.json"))
        adr = [a for a, _, _ in j["mem"] if base <= a < base + 32000]
        x0, y0 = coords[slot]
        groups = {((a - base) % 160) // 8 for a in adr}
        steps.append(j["steps"])
        ok += bool(adr) and {(a - base) // 160 for a in adr} == {y0} and groups <= set(range(x0 // 16, (x0 + 31) // 16 + 1))
        drawn += bool(adr)
    print(f"slot {slot} {coords[slot]}: steps {steps}, frames with pixels inside the predicted row/groups {ok}/4")
print(f"{drawn}/24 calls wrote backdrop pixels (expected 17)")
