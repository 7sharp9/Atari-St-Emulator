"""gate_aggr.py: is the group aggression word (record +148 + 2k, group view 72) read by anything that changes state?

Differential run on the real 68000: from a snapshot, run N steps with the 30 aggression words (5 sides x 6 groups) as they are (control)
and with all of them poked to a value (0, 7, mixed); diff the two final RAM images ignoring the 30 words.  A reader that feeds any
decision, counter or random draw shows up as a difference elsewhere (the emulator is deterministic; `--control` runs the control twice
to prove it).  The panel of the captain is not drawn unless the player opens it, so a display reader does not show.

    cd M68000 && python3 reversing/powermonger/py/aggr/gate_aggr.py <snap> <steps> [value ...]   (values: hex words, 'mix' = 0..7 by group)
Positive controls: AGGR_FIELD=136 (posture) or 112 (food) must show differing bytes. Output: $PM_WORK/aggr/.
"""
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(os.environ.get("M68000_ROOT", Path(__file__).resolve().parents[4]))
sys.path.insert(0, str(ROOT / "tools"))
from disassemble import ram_from_snap  # noqa: E402

DISK = "scratchpad/powermonger.st"
OUT = (ROOT / os.environ.get("PM_WORK", "scratchpad/pmwork")) / "aggr"   # $PM_WORK/aggr (default scratchpad/pmwork/aggr), one .snap per run
G = 0x51538
REC = 0x13c
FIELD = int(os.environ.get("AGGR_FIELD", "148"))   # 148 = aggression; other values give positive controls (112 food, 136 posture)


def words():
    return [G + s * REC + FIELD + 2 * k for s in range(5) for k in range(6)]


def pokes(val):
    cmds = []
    for s in range(5):
        for j in range(3):  # three longwords per record: groups (0,1) (2,3) (4,5)
            a = G + s * REC + FIELD + 4 * j
            if val == "mix":
                v = ((2 * j + s) % 8) << 16 | ((2 * j + 1 + s) % 8)
            else:
                v = (val << 16) | val
            cmds.append("w %x %08x" % (a, v))
    return cmds


def run(snap, steps, val, tag):
    OUT.mkdir(parents=True, exist_ok=True)
    out = OUT / (tag + ".snap")
    cmds = (pokes(val) if val is not None else []) + ["s %d" % steps, "snap %s" % out]
    argv = ["dotnet", "exec", "bin/Debug/net8.0/M68000.dll", "resume", snap, "repl", "--disk-a", DISK]
    p = subprocess.run(argv, input="".join(c + "\n" for c in cmds) + "q\n", capture_output=True, text=True, cwd=ROOT, timeout=3000,
                       env=dict(os.environ, ATARI_NOTRACE="1"))
    return out, p.stdout + p.stderr


def diff(a, b):
    ra, rb = ram_from_snap(a), ram_from_snap(b)
    skip = set()
    for w in words():
        skip.update((w, w + 1))
    d = [i for i in range(min(len(ra), len(rb))) if ra[i] != rb[i] and i not in skip]
    return d


if __name__ == "__main__":
    snap, steps = sys.argv[1], int(sys.argv[2])
    vals = sys.argv[3:] or ["0", "7", "mix"]
    bad = 0
    name = Path(snap).stem
    ctl, o = run(snap, steps, None, "%s_%d_f%d_ctl" % (name, steps, FIELD))
    ctl2, _ = run(snap, steps, None, "%s_%d_f%d_ctl2" % (name, steps, FIELD))
    print("determinism: control vs control differing bytes:", len(diff(ctl, ctl2)))
    for v in vals:
        val = "mix" if v == "mix" else int(v, 16)
        f, o = run(snap, steps, val, "%s_%d_f%d_v%s" % (name, steps, FIELD, v))
        d = diff(ctl, f)
        bad += len(d)
        print("variant %s: %d bytes differ outside the 30 words" % (v, len(d)), ("first: " + " ".join("$%x" % i for i in d[:12])) if d else "")
    if FIELD == 148:
        print("RESULT %s" % ("PASS: aggression word read by nothing (0 differing bytes in %d variants)" % len(vals) if bad == 0 else "FAIL: %d bytes differ" % bad))
