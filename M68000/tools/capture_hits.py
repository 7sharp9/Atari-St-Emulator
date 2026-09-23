"""Snapshot a routine at chosen natural hits, with its entry registers.

The corpus-building step of every callcap differential test: resume a start
snapshot, stop at the n-th time PC reaches <addr> (`bpc`), record the entry
registers and the return address at (A7), snapshot, and repeat for the next
chosen hit.  Writes <out>/<name>_<n>.snap + .ram (raw RAM, what
pm_fsm_diff.Harness reads) for each hit reached, and <out>/<name>.json:

    [{"hit": n, "snap": ".../<name>_<n>.snap", "ram": "...", "ret": 0x5654,
      "regs": {"D0": ..., "A7": ...}}, ...]

so a gate builds State(..., presets={"A3": e["regs"]["A3"]}) without
re-parsing REPL logs.  Hit numbers count from the start snapshot (take them
from a `hits` census line: `count first last`).  Run from M68000/:

    py -3 tools/capture_hits.py scratchpad/pm121/run/k25_s3.snap 2776 1,2 scratchpad/x --name k25_s4
    py -3 tools/capture_hits.py <snap> <addr> <n,...> <out> [--name N] [--max STEPS] [--disk IMG] [--pre CMD]...

--pre adds REPL commands before the first bpc (a poke, `watch`, ...).  The
REPL log is kept as <out>/<name>.log.  A hit that is not reached within
--max steps of the previous one is reported and skipped.
"""
import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from disassemble import ram_from_snap

M68 = Path(__file__).resolve().parents[1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("snap")
    ap.add_argument("addr")
    ap.add_argument("hits", help="comma-separated ascending hit numbers, counted from the start snapshot")
    ap.add_argument("out")
    ap.add_argument("--name", default=None)
    ap.add_argument("--max", type=int, default=50_000_000, help="step cap per bpc")
    ap.add_argument("--disk", default="scratchpad/powermonger.st")
    ap.add_argument("--pre", action="append", default=[])
    a = ap.parse_args()

    addr = a.addr.lower().lstrip("$")
    hits = [int(h) for h in a.hits.split(",")]
    assert hits == sorted(hits) and len(set(hits)) == len(hits) and hits[0] >= 1, "hits must ascend from 1"
    name = a.name or f"{Path(a.snap).stem}_{addr}"
    out = Path(a.out)
    (M68 / out).mkdir(parents=True, exist_ok=True)

    cmds, prev = list(a.pre), 0
    for n in hits:
        cmds += [f"bpc {addr} {n - prev} {a.max}", "bt 1", f"snap {out.as_posix()}/{name}_{n}.snap"]
        prev = n
    cmds.append("q")
    env = dict(os.environ, ATARI_NOTRACE="1")
    p = subprocess.run(["dotnet", "exec", "bin/Debug/net8.0/M68000.dll", "resume", a.snap, "repl",
                        "--disk-a", a.disk], input="\n".join(cmds) + "\n", capture_output=True,
                       text=True, cwd=M68, env=env)
    log = p.stdout + p.stderr
    (M68 / out / f"{name}.log").write_text(log)

    # one block per bpc: "--- breakpoint $... hit (k/k) ..." or "--- gave up ..."
    blocks = re.split(r"(?=^--- (?:breakpoint|gave up))", log, flags=re.M)[1:]
    entries = []
    for n, b in zip(hits, blocks):
        if b.startswith("--- gave up"):
            print(f"{name}: hit {n} of ${addr} not reached within {a.max} steps; stopping")
            break
        regs = {k: int(v, 16) for k, v in re.findall(r"\b([DA][0-7]):([0-9a-f]{8})", b)}
        ret = re.search(r"return address \(A7\) = \$([0-9a-f]+)", b)
        snap = f"{out.as_posix()}/{name}_{n}.snap"
        ram = snap[:-5] + ".ram"
        (M68 / ram).write_bytes(ram_from_snap(str(M68 / snap)))
        entries.append({"hit": n, "snap": snap, "ram": ram,
                        "ret": int(ret.group(1), 16) if ret else None, "regs": regs})
        print(f"{name}_{n}: ret=${entries[-1]['ret'] or 0:x} "
              + " ".join(f"{k}={v:x}" for k, v in regs.items() if k in ("A0", "A1", "A3", "D1", "D3")))
    (M68 / out / f"{name}.json").write_text(json.dumps(entries, indent=1))
    if len(entries) < len(hits):
        sys.exit(1)


if __name__ == "__main__":
    main()
