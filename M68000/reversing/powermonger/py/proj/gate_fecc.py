"""Gate: the grid-corner projector `$fecc` (+ `$fe8e` HBIAS, `$ff7c` divide) against `proj_ref.project()`.

36 generated states (camera cell `(cx, cy)` poked into `$4bb3a`, `callcap fecc 300000 ... A3=13f8a` on `pm78_settle.snap`, full
changed-memory comparison of the 81-vertex x 2-word corner buffer `$3f364`) plus the 4 captured corner buffers of
`pm73_fight`, `pm74_late`, `pm78_settle`, `pm88_f1` (`proj_ref.py <ram>` against the stored `$3f364`). Expect `3240/3240` vertices.

    cd M68000 && uv run python reversing/powermonger/py/proj/gate_fecc.py

Promoted from `scratchpad/pm92/diff_fecc.py` (which drove `run.ps1`); runs the raw `dotnet exec` form with `ATARI_NOTRACE=1`. The callcap JSONs
go to `scratchpad/pm147/proj/`. `callcap` does not need a disk for this routine.
"""
import json
import os
import struct
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import proj_ref

M68 = Path(os.environ.get("M68000_ROOT") or Path(__file__).resolve().parents[4])
SCR = M68 / "scratchpad"
OUT = SCR / "pm147" / "proj"
BASE_SNAP = "scratchpad/pm78_settle.snap"
BASE_RAM = SCR / "pm78_settle.ram"
CAPTURES = ["pm73_fight", "pm74_late", "pm78_settle", "pm88_f1"]
CORPUS = [(cx, cy) for cx in (16, 24, 32, 40, 48, 56) for cy in (20, 30, 40, 51, 60, 70)]


def run_repl(cmds):
    p = subprocess.run(
        ["dotnet", "exec", "bin/Debug/net8.0/M68000.dll", "resume", BASE_SNAP, "repl"],
        input="".join(c + "\n" for c in cmds) + "q\n",
        capture_output=True, text=True, cwd=M68, timeout=300,
        env={**os.environ, "ATARI_NOTRACE": "1"})
    return p.stdout + p.stderr


def apply_delta(buf, mem):
    for ad, _before, after in mem:
        if 0x3f364 <= ad < 0x3f364 + 9 * 64:
            buf[ad - 0x3f364] = after
    return buf


def corners_from_buf(buf, half=4):
    out = {}
    for gr in range(2 * half + 1):
        b = gr * 64
        for gc in range(2 * half + 1):
            out[(gr, gc)] = struct.unpack_from(">HH", buf, b + gc * 4)
    return out


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    ram0 = proj_ref.Ram(str(BASE_RAM))
    total = ok = 0
    fails = []
    for cx, cy in CORPUS:
        word = (cx << 16) | cy
        out = OUT / f"d_{cx}_{cy}.json"
        out.unlink(missing_ok=True)
        log = run_repl([f"w 4bb3a {word:08x}",
                        f"callcap fecc 300000 {out.relative_to(M68)} A3=13f8a"])
        if not out.exists():
            print(f"({cx},{cy}) NO OUTPUT\n{log[-400:]}")
            fails.append(((cx, cy), "no output", None, None))
            continue
        j = json.load(open(out))
        real = corners_from_buf(apply_delta(bytearray(ram0.r[0x3f364:0x3f364 + 9 * 64]), j["mem"]))
        recon, _ = proj_ref.project(ram0, cx, cy)
        bad = [k for k in recon if recon[k] != real[k]]
        total += len(recon)
        ok += len(recon) - len(bad)
        fails += [((cx, cy), k, recon[k], real[k]) for k in bad]
        print(f"({cx:2d},{cy:2d}) {j['outcome'][:16]:16} {'ok' if not bad else 'MISMATCH'}")
    for name in CAPTURES:
        ram = proj_ref.Ram(str(SCR / f"{name}.ram"))
        recon, half = proj_ref.project(ram)
        stored = proj_ref.stored_corners(ram, half)
        bad = [k for k in recon if recon[k] != stored[k]]
        total += len(recon)
        ok += len(recon) - len(bad)
        fails += [(name, k, recon[k], stored[k]) for k in bad]
        print(f"{name:12} stored corner buffer {'ok' if not bad else 'MISMATCH'}")
    print(f"\nVERTICES: {ok}/{total} identical ({len(CORPUS)} generated states + {len(CAPTURES)} captures)")
    for f in fails[:20]:
        print("  ", f)
    sys.exit(0 if ok == total and not fails else 1)


if __name__ == "__main__":
    main()
