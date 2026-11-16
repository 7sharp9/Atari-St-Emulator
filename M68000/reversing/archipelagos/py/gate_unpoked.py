"""Gate: Archipelagos loads without its two pokes (README "The emulator gap and the two pokes").

Runs reversing/archipelagos/drive.txt twice from a cold boot on the current build, as written (poked) and with its
four `ww` lines removed (unpoked), each on its own copy of the disk, writing snapshots under
scratchpad/archipelagos/gate_unpoked/{poked,unpoked}/. Then compares RAM: `at1301c` may differ only in the POKE 1
bytes $7047a..$7047d, and `m2` only in the POKE 2 bytes $13578..$1357b and the stale stack bytes $2f43..$2f49
below the stack pointer. Also prints the step count of the unpoked run's `bp 1301c`.
Needs scratchpad/archipelagos/tmb58.st. Finds M68000/ by walking up to tools/rdis.py (or M68000_ROOT).
"""
import os, re, shutil, subprocess, sys
from pathlib import Path

ROOT = Path(os.environ["M68000_ROOT"]) if os.environ.get("M68000_ROOT") else \
    next(d for d in Path(__file__).resolve().parents if (d / "tools" / "rdis.py").exists())
sys.path.insert(0, str(ROOT / "tools"))
from gfxview import load_ram  # noqa: E402

DLL = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else ROOT / "bin/Debug/net8.0/M68000.dll"  # argv[1]: another build, for a control
OUT = ROOT / "scratchpad/archipelagos/gate_unpoked"
drive = (ROOT / "reversing/archipelagos/drive.txt").read_text().splitlines()
procs = {}
for kind in ("poked", "unpoked"):
    d = OUT / kind
    if d.exists():
        shutil.rmtree(d)
    d.mkdir(parents=True)
    shutil.copy(ROOT / "scratchpad/archipelagos/tmb58.st", d / "tmb58.st")
    lines = [re.sub(r"scratchpad/archipelagos/", f"scratchpad/archipelagos/gate_unpoked/{kind}/", l) for l in drive]
    if kind == "unpoked":
        lines = [l for l in lines if not l.startswith("ww ")]
    env = dict(os.environ, ATARI_NOTRACE="1")
    procs[kind] = subprocess.Popen(["dotnet", "exec", str(DLL), "30000000", "repl", "--disk-a", str(d / "tmb58.st")],
                                   stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                   text=True, cwd=ROOT, env=env)
    procs[kind].stdin.write("\n".join(lines) + "\n")
    procs[kind].stdin.close()
outs = {k: p.stdout.read() for k, p in procs.items()}
for k, p in procs.items():
    if p.wait() != 0:
        sys.exit(f"{k} run exited {p.returncode}")
m = re.search(r"breakpoint \$0001301c hit \(\d+/\d+\) after (\d+) step", outs["unpoked"])
print(f"unpoked bp 1301c: {'reached after ' + m.group(1) + ' steps' if m else 'not reached'}")


def diff(name, allowed):
    a = load_ram(str(OUT / "poked" / f"{name}.snap"))[0]
    b = load_ram(str(OUT / "unpoked" / f"{name}.snap"))[0]
    d = [i for i in range(min(len(a), len(b))) if a[i] != b[i]]
    ok = sum(1 for i in d if any(lo <= i <= hi for lo, hi in allowed))
    print(f"{name}: differing RAM bytes inside the allowed ranges {ok}/{len(d)}" +
          ("" if ok == len(d) else "  outside: " + " ".join(f"${i:x}" for i in d if not any(lo <= i <= hi for lo, hi in allowed))[:200]))


diff("at1301c", [(0x7047a, 0x7047d)])
diff("m2", [(0x13578, 0x1357b), (0x2f43, 0x2f49)])
