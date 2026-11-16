"""Gate: plain `mouse move` / `mouse down|up` drive Carrier Command (README "Mouse input").

Needs the MFP in-service registers and paced IKBD bytes (DEVELOPING.md "IKBD command interpreter"). Two runs:
  1. from scratchpad/carrier/c_eng.snap, `mouse move 0 -55` and 400,000 steps: the pointer ($476/$478) goes
     (160,100) -> (160,45), the c_mv.snap position; a build without them leaves it at (160,100).
  2. from c80.snap, drive.txt with its per-byte mouse bytes replaced by plain mouse commands: $1244 = $ff
     (the Strategy game); 0 on the older build.
Run from anywhere; finds M68000/ by walking up to tools/rdis.py (or M68000_ROOT).
"""
import os, re, subprocess, sys
from pathlib import Path

ROOT = Path(os.environ["M68000_ROOT"]) if os.environ.get("M68000_ROOT") else \
    next(d for d in Path(__file__).resolve().parents if (d / "tools" / "rdis.py").exists())
DLL = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else ROOT / "bin/Debug/net8.0/M68000.dll"  # argv[1]: another build, for a control
W = "scratchpad/carrier"


def repl(snap, lines):
    env = dict(os.environ, ATARI_NOTRACE="1")
    p = subprocess.run(["dotnet", "exec", str(DLL), "resume", f"{W}/{snap}", "repl", "--disk-a", f"{W}/carrier_auto.st"],
                       input="\n".join(lines + ["q"]) + "\n", capture_output=True, text=True, cwd=ROOT, env=env)
    dumps = re.findall(r"(?m)^((?:[0-9a-f]{2} ?)+)$", p.stdout)
    return p.returncode, [bytes.fromhex(d.replace(" ", "")) for d in dumps]


def xy(b):
    return int.from_bytes(b[0:2], "big"), int.from_bytes(b[2:4], "big")


rc, d = repl("c_eng.snap", ["m 476 4", "mouse move 0 -55", "s 400000", "m 476 4"])
if rc != 0 or len(d) < 2:
    sys.exit(f"run 1 failed: rc={rc}, {len(d)} dumps")
(x0, y0), (x1, y1) = xy(d[0]), xy(d[1])
print(f"plain mouse move: pointer ({x0},{y0}) -> ({x1},{y1})")

rc, d = repl("c80.snap", ["kbd 02", "s 400000", "kbd 82", "s 60000000", "mouse move 0 -55", "s 400000",
                          "mouse down l", "s 100000", "mouse up l", "s 30000000", "m 1244 1"])
if rc != 0 or len(d) < 1:
    sys.exit(f"run 2 failed: rc={rc}, {len(d)} dumps")
print(f"plain-mouse drive: $1244 = {d[-1][0]:02x}")
