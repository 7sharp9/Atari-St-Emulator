"""Callcap corpus of `$1abaa` (`_seasons`): N consecutive natural calls from a start snapshot.

For every call k = 1..N: `bpc 1abaa 1`, `snap` (the pre-state), `callcap 1abaa` (the 68000's delta,
interrupts masked, state restored), then on to the next natural call.  Each pre-state is stored as
<out>/cNNNN.ram.gz (full 1 MB RAM) next to the callcap delta <out>/cNNNN.json, and the 1 MB .snap is
deleted.  index.json lists the calls.

A wrap call (`$57ff6` LCG reaches 0) reaches the sample player, whose `$1ae40` loop spins while
byte `$2c993` != 0; under callcap (IPL 7) no interrupt clears it, so the callcap hits its step cap.
For each such call the script reruns it from its own pre-state snapshot with the labelled poke
`$2c993 := 0` (a longword `w 2c992` that keeps `$2c992`, `$2c994`, `$2c995` as read from that
snapshot) and stores the poked pre-state instead (`"poke2c993": true` in index.json).  The natural
lineage is unaffected: callcap restores the state before the next `bpc`.

    cd M68000 && uv run python <this> <snap> <ncalls> <arm> [--pre "w 57fd0 00060000"]... [--pre-file f]

The four arms of the gate:
    capture_1abaa.py scratchpad/pm123/win/m1_ready.snap 420 m1
    capture_1abaa.py scratchpad/pm142/rand1.snap 420 rand1
    capture_1abaa.py scratchpad/pm142/rand1.snap 240 wrapw --pre "w 57fd0 00060188" --pre "w 57ff4 14820681"
    capture_1abaa.py scratchpad/pm142/rand1.snap 4 felled --pre "w 57ff4 14820681" --pre-file <py/season>/felled_pre.txt

Output: $PM_WORK/corpus/<arm>/ (PM_WORK default scratchpad/season).
"""
import argparse
import gzip
import json
import os
import re
import struct
import subprocess
import sys
from pathlib import Path


def repo_root():
    p = Path(__file__).resolve()
    for d in [p, *p.parents]:
        if (d / "tools" / "rdis.py").exists():
            return d
        if (d / "M68000" / "tools" / "rdis.py").exists():
            return d / "M68000"
    return Path(os.environ["M68000_ROOT"])


ROOT = repo_root()
sys.path.insert(0, str(ROOT / "tools"))
from disassemble import ram_from_snap  # noqa: E402

WORK = Path(os.environ.get("PM_WORK", "scratchpad/season"))
CAP = 400_000          # callcap steps: a call with a weather draw costs about 25k
BPC_MAX = 20_000_000   # steps to the next natural call


def run(snap, cmds, log):
    env = dict(os.environ, ATARI_NOTRACE="1")
    p = subprocess.run(["dotnet", "exec", "bin/Debug/net8.0/M68000.dll", "resume", str(snap), "repl"],
                       input="\n".join(cmds + ["q"]) + "\n", capture_output=True, text=True, cwd=ROOT, env=env)
    (ROOT / log).write_text(p.stdout + p.stderr)
    return p.stdout + p.stderr


def store(out, k, snap):
    ram = ram_from_snap(str(ROOT / snap))
    with gzip.open(ROOT / out / f"c{k:04d}.ram.gz", "wb", compresslevel=6) as f:
        f.write(ram)
    (ROOT / snap).unlink()
    return ram


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("snap")
    ap.add_argument("ncalls", type=int)
    ap.add_argument("arm")
    ap.add_argument("--pre", action="append", default=[], help="REPL lines before the first bpc (labelled pokes)")
    ap.add_argument("--pre-file", help="file of further --pre lines (felled_pre.txt: every live tree's +7 := $0d on rand1)")
    a = ap.parse_args()
    out = WORK / "corpus" / a.arm
    (ROOT / out).mkdir(parents=True, exist_ok=True)

    if a.pre_file:
        a.pre += [l.strip() for l in open(a.pre_file) if l.strip()]
    cmds = ["disk scratchpad/powermonger.st", *a.pre]
    for k in range(1, a.ncalls + 1):
        cmds += [f"bpc 1abaa 1 {BPC_MAX}", f"snap {out}/c{k:04d}.snap", f"callcap 1abaa {CAP} {out}/c{k:04d}.json"]
    log = run(a.snap, cmds, out / "capture.log")
    stops = re.findall(r"--- breakpoint \$0001abaa hit \(1/1\) after (\d+) step", log)
    index, step = [], 0
    for k in range(1, a.ncalls + 1):
        js = ROOT / out / f"c{k:04d}.json"
        sn = out / f"c{k:04d}.snap"
        if not js.exists() or not (ROOT / sn).exists():
            print(f"{a.arm}: call {k} not captured; stopping")
            break
        step += int(stops[k - 1])
        j = json.load(open(js))
        e = {"k": k, "step": step, "poke2c993": False}
        if j["outcome"] != "returned":
            ram = ram_from_snap(str(ROOT / sn))
            lw = struct.unpack(">I", ram[0x2c992:0x2c996])[0] & 0xff00ffff
            print(f"{a.arm}: call {k} {j['outcome']}; byte $2c993 = ${ram[0x2c993]:02x}, rerun with w 2c992 {lw:08x}")
            pk = out / f"c{k:04d}p.snap"
            run(sn, [f"w 2c992 {lw:08x}", f"snap {pk}", f"callcap 1abaa {CAP} {out}/c{k:04d}.json"],
                out / f"c{k:04d}p.log")
            (ROOT / sn).unlink()
            sn = pk
            e["poke2c993"] = True
            j = json.load(open(js))
            assert j["outcome"] == "returned", (k, j["outcome"])
        store(out, k, sn)
        e["nmem"] = len(j["mem"])
        index.append(e)
    (ROOT / out / "index.json").write_text(json.dumps({"snap": a.snap, "pre": a.pre, "calls": index}, indent=0))
    print(f"{a.arm}: {len(index)} calls, {sum(e['poke2c993'] for e in index)} poked wrap call(s), "
          f"{sum(e['nmem'] > 4 for e in index)} with more than 4 bytes changed, last at step {step}")


if __name__ == "__main__":
    main()
