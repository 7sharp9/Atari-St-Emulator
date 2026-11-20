"""Which code runs in which situation: a census of executed bytes and call targets per labelled run,
and the code that one group of runs reaches and another does not.

Use it to ask "does level 5 (wave 4, the shop, the ending) run code that level 1 never does?", "what code
does this input reach that its no-input control does not?", or "what has no run of ours ever executed?".
Counting how much code runs is the cheap part; the difference between two groups of runs is the useful
one, because it lists the routines a situation adds, ranked by size, for reading.

    # 1. one census run: resume a snapshot, run a REPL fragment per chunk with ATARI_TRACE_EVENTS on,
    #    reduce each chunk's event log to an .npz (coverage bitmap + call targets), delete the log.
    python tools/code_census.py run <snap> <outdir>/<label> --chunks 8 [--per-chunk frag.txt | --steps 5000000]
        [--disk-a <img>] [--read 17846:2 --read 1f00c:2] [--stop-if 1f00c:2==0000] [--stop-if-changed 17846:2]

    # 2. compare groups of runs over a code window
    python tools/code_census.py report --range a2fc 1f274 --sym <game>.sym \
        --group L0=<outdir>/L0 --group L1=<outdir>/L1 ... [--base L0] [--gap 16] [--min 8] [--json out.json]

`run` writes `<outdir>/<label>/chunk_NNN.npz` and appends one JSON line per chunk to `<outdir>/<label>/meta.jsonl`
(the `--read` values at the chunk's end). Chunks chain through a rolling snapshot `<label>/roll.snap`, so a long
run is many short processes and no event log grows past one chunk (about 6.6 MB per million steps). The fragment
file is REPL text run verbatim once per chunk (it must step the machine itself; `--steps N` is shorthand for
`s N`); the tool appends the `--read` lines, `snap` and `q`. A `--read` value is taken from the last hex-only
output lines, so a fragment that prints its own `m` lines must come before them (it does: reads are appended).
`--stop-if A:L==HEX` / `!=HEX` and `--stop-if-changed A:L` end the run after the chunk where they first hold
(a game over that falls into an attract demo would mix the demo's code into the run). Pokes in a fragment are
the user's to label.

`report` prints, per group, the chunks, steps, executed bytes and call targets inside the window; then every
span of bytes that some group ran and the base group (or, with no base, every other group) did not, merged across
gaps of `--gap` bytes, with the groups that ran it, the nearest call target at or below it ("routine") and the
nearest `.sym` name. Spans are what the census found, bounded by the runs it was given: "the base never ran X"
means none of the base's runs did.

Coverage is from flow records only (every branch, call, return, trap, interrupt): bytes between one record's
target and the next record's pc ran sequentially; a terminator's own operand words beyond its opcode word are
counted only for Bcc (lower bound). Exact byte coverage needs ATARI_TRACE_EVENTS_ALL=1 (5x the log); this tool
does not set it. Record layout: tools/trace_cfg.py. Adapted from reversing/virus/py/census/reduce_evt.py, which
Virus's census gate still uses.
"""
import argparse
import bisect
import glob
import json
import os
import re
import shutil
import subprocess
import sys

import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
DLL = os.path.join(ROOT, "bin", "Debug", "net8.0", "M68000.dll")
DT = np.dtype([("step", "<u8"), ("pc", "<u4"), ("tgt", "<u4"), ("op", "<u2"), ("kind", "u1"), ("fl", "u1")])
HDR = 16
MAXA = 0x1000000  # 24-bit bus; the bitmap is 2 MB packed, sliced to the window in report


def reduce_events(path):
    raw = np.fromfile(path, dtype=np.uint8)
    if raw[:4].tobytes() != b"A68E":
        raise ValueError(f"{path}: not an ATARI_TRACE_EVENTS log")
    rec = raw[HDR:HDR + (len(raw) - HDR) // 20 * 20].view(DT)
    out = {"nrec": len(rec), "step0": int(rec["step"][0]) if len(rec) else 0,
           "step1": int(rec["step"][-1]) if len(rec) else 0}
    pc = (rec["pc"] & 0xFFFFFF).astype(np.int64)
    tg = (rec["tgt"] & 0xFFFFFF).astype(np.int64)
    op = rec["op"].astype(np.int64)
    kind = rec["kind"]
    call = kind == 3
    direct = call & (((op >> 8) == 0x61) | (((op >> 3) & 7) == 7))
    for name, m in (("direct", direct), ("indirect", call & ~direct), ("int", kind == 6)):
        t, n = np.unique(tg[m], return_counts=True)
        out[name + "_t"], out[name + "_n"] = t, n
    start = tg[:-1]
    oplen = np.where((op[1:] >> 12) == 6,
                     np.where((op[1:] & 0xFF) == 0, 4, np.where((op[1:] & 0xFF) == 0xFF, 6, 2)), 2)
    end = pc[1:] + oplen
    ok = (end > start) & (end - start < 0x10000) & (start < MAXA)
    out["span_bad"] = int((~ok).sum())
    sp = np.unique(np.stack([start[ok], np.minimum(end[ok], MAXA)]).T, axis=0)
    diff = np.zeros(MAXA + 1, np.int32)
    np.add.at(diff, sp[:, 0], 1)
    np.add.at(diff, sp[:, 1], -1)
    out["cover"] = np.packbits(np.cumsum(diff)[:MAXA] > 0)
    return out


def parse_rd(s):
    a, l = s.split(":")
    return int(a, 16), int(l)


def cmd_run(a):
    outdir = os.path.abspath(a.outdir)
    os.makedirs(outdir, exist_ok=True)
    frag = open(a.per_chunk).read().rstrip("\n") + "\n" if a.per_chunk else f"s {a.steps}\n"
    reads = [parse_rd(r) for r in a.read]
    stops = []
    for s in a.stop_if:
        m = re.fullmatch(r"([0-9a-fA-F]+:\d+)(==|!=)([0-9a-fA-F]+)", s)
        if not m:
            sys.exit(f"bad --stop-if {s!r}: want ADDR:LEN==HEX or ADDR:LEN!=HEX")
        stops.append((m.group(1), m.group(2), m.group(3).lower()))
    for s in a.stop_if_changed:
        stops.append((s, "changed", None))
    allreads = reads + [parse_rd(k) for k, _, _ in stops if parse_rd(k) not in reads]
    keys = [f"{x:x}:{l}" for x, l in allreads]
    cur, first = os.path.abspath(a.snap), {}
    roll = os.path.join(outdir, "roll.snap")
    env = dict(os.environ, ATARI_NOTRACE="1")
    disk = ["--disk-a", os.path.abspath(a.disk_a)] if a.disk_a else []
    for i in range(a.chunks):
        evt = os.path.join(outdir, f"chunk_{i:03d}.evt")
        new = roll + ".new"
        script = frag + "".join(f"m {x:x} {l}\n" for x, l in allreads) + f"snap {new}\nq\n"
        p = subprocess.run(["dotnet", "exec", a.dll, "resume", cur, "repl", *disk], input=script, text=True,
                           capture_output=True, cwd=ROOT, env=dict(env, ATARI_TRACE_EVENTS=evt))
        if p.returncode != 0 or not os.path.exists(new):
            sys.exit(f"chunk {i} failed (rc {p.returncode}):\n{(p.stdout + p.stderr)[-2000:]}")
        shutil.move(new, roll)
        if os.path.exists(new + ".prov.json"):
            shutil.move(new + ".prov.json", roll + ".prov.json")
        cur = roll
        hexl = [l.strip() for l in p.stdout.splitlines() if re.fullmatch(r"[0-9a-f]{2}( [0-9a-f]{2})*", l.strip())]
        vals = dict(zip(keys, [h.replace(" ", "") for h in hexl[-len(keys):]])) if keys else {}
        if keys and len(hexl) < len(keys):
            sys.exit(f"chunk {i}: expected {len(keys)} read lines, got {len(hexl)}")
        o = reduce_events(evt)
        np.savez_compressed(os.path.join(outdir, f"chunk_{i:03d}.npz"), **o)
        os.remove(evt)
        meta = {"chunk": i, "snap": os.path.abspath(a.snap), "steps": [o["step0"], o["step1"]],
                "nrec": o["nrec"], "span_bad": o["span_bad"], "reads": vals}
        with open(os.path.join(outdir, "meta.jsonl"), "a") as f:
            f.write(json.dumps(meta) + "\n")
        print(f"{os.path.basename(outdir)} chunk {i}: {o['nrec']} records, reads {vals}", flush=True)
        if i == 0:
            first = vals
        hit = []
        for k, opn, v in stops:
            if (opn == "==" and vals[k] == v) or (opn == "!=" and vals[k] != v) or \
               (opn == "changed" and vals[k] != first.get(k)):
                hit.append(f"{k} {opn} {v or first.get(k)}")
        if hit:
            print(f"stopped after chunk {i}: {', '.join(hit)}")
            break


def load_group(path):
    files = sorted(glob.glob(os.path.join(path, "chunk_*.npz"))) if os.path.isdir(path) else sorted(glob.glob(path))
    if not files:
        sys.exit(f"no chunk_*.npz under {path}")
    cov, targets, steps = None, {}, 0
    for fn in files:
        z = np.load(fn)
        c = np.unpackbits(z["cover"])[:MAXA].astype(bool)
        cov = c if cov is None else cov | c
        for kind in ("direct", "indirect"):
            for t, n in zip(z[kind + "_t"], z[kind + "_n"]):
                targets[int(t)] = targets.get(int(t), 0) + int(n)
        steps += int(z["step1"]) - int(z["step0"])
    return {"files": len(files), "cover": cov, "targets": targets, "steps": steps}


def load_sym(paths):
    syms = []
    for p in paths:
        for line in open(p):
            m = re.match(r"\s*\$?([0-9a-fA-F]+)\s+(\S+)", line)
            if m and not line.lstrip().startswith("#"):
                syms.append((int(m.group(1), 16), m.group(2)))
    syms.sort()
    return syms


def spans_of(mask, lo, gap):
    idx = np.flatnonzero(mask)
    if not len(idx):
        return []
    brk = np.flatnonzero(np.diff(idx) > gap + 1)
    starts = np.r_[idx[0], idx[brk + 1]]
    ends = np.r_[idx[brk], idx[-1]] + 1
    return [(int(s) + lo, int(e) + lo, int(mask[s:e].sum())) for s, e in zip(starts, ends)]


def cmd_report(a):
    lo, hi = int(a.range[0], 16), int(a.range[1], 16)
    groups = {}
    for g in a.group:
        name, path = g.split("=", 1)
        groups[name] = load_group(path)
    syms = load_sym(a.sym)
    sym_addrs = [s for s, _ in syms]
    all_t = sorted({t for g in groups.values() for t in g["targets"] if lo <= t < hi})

    def where(x):
        r = all_t[bisect.bisect_right(all_t, x) - 1] if all_t and all_t[0] <= x else None
        i = bisect.bisect_right(sym_addrs, x) - 1
        s = f"{syms[i][1]}+{x - syms[i][0]:x}" if i >= 0 and x - syms[i][0] < 0x2000 else ""
        return r, s

    print(f"window ${lo:x}..${hi:x} ({hi - lo} bytes); flow-only coverage, a lower bound")
    print(f"{'group':12} {'chunks':>6} {'steps':>12} {'bytes run':>10} {'% window':>8} {'targets':>8}")
    rows = {}
    for n, g in groups.items():
        c = g["cover"][lo:hi]
        nt = sum(1 for t in g["targets"] if lo <= t < hi)
        rows[n] = {"chunks": g["files"], "steps": g["steps"], "bytes": int(c.sum()), "targets": nt}
        print(f"{n:12} {g['files']:6} {g['steps']:12} {int(c.sum()):10} {100 * c.sum() / (hi - lo):7.1f}% {nt:8}")
    union = np.zeros(hi - lo, bool)
    for g in groups.values():
        union |= g["cover"][lo:hi]
    print(f"{'(union)':12} {'':6} {'':12} {int(union.sum()):10} {100 * union.sum() / (hi - lo):7.1f}%")

    result = {"window": [lo, hi], "groups": rows, "new": {}}
    names = list(groups)
    if a.base:
        if a.base not in groups:
            sys.exit(f"--base {a.base} is not a group")
        base = groups[a.base]["cover"][lo:hi]
        others = [n for n in names if n != a.base]
        print(f"\nbytes each group ran that {a.base} did not; and that no other group ran either (unique):")
        for n in others:
            c = groups[n]["cover"][lo:hi]
            rest = np.zeros_like(c)
            for m in names:
                if m != n:
                    rest |= groups[m]["cover"][lo:hi]
            nt = sorted(t for t in groups[n]["targets"] if lo <= t < hi and t not in groups[a.base]["targets"])
            print(f"  {n:10} not in {a.base}: {int((c & ~base).sum()):6} bytes, {len(nt):3} call targets;"
                  f" unique {int((c & ~rest).sum()):6} bytes")
        new = union & ~base
        label = f"not run in {a.base}"
    else:
        new = None
        label = "run by exactly one group"
        cnt = np.zeros(hi - lo, np.int32)
        for g in groups.values():
            cnt += g["cover"][lo:hi]
        new = cnt == 1
    sp = [s for s in spans_of(new, lo, a.gap) if s[2] >= a.min]
    sp.sort(key=lambda s: -s[2])
    print(f"\nspans {label} (gap {a.gap}, min {a.min} bytes): {len(sp)}, {sum(s[2] for s in sp)} bytes")
    print(f"  {'span':19} {'bytes':>6}  {'routine':>8}  {'sym':28} groups")
    out = []
    for s, e, nb in sp[:a.top]:
        who = [n for n in names if groups[n]["cover"][s:e].any() and (not a.base or n != a.base)]
        r, sym = where(s)
        print(f"  ${s:06x}..${e:06x} {nb:6}  {('$%06x' % r) if r is not None else '':>8}  {sym:28} {' '.join(who)}")
        out.append({"lo": s, "hi": e, "bytes": nb, "routine": r, "sym": sym, "groups": who})
    if len(sp) > a.top:
        print(f"  ... {len(sp) - a.top} more (--top)")
    result["new"] = {"label": label, "spans": out, "total_spans": len(sp)}
    if a.json:
        with open(a.json, "w") as f:
            json.dump(result, f, indent=1)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("snap")
    r.add_argument("outdir")
    r.add_argument("--chunks", type=int, default=1)
    r.add_argument("--steps", type=int, default=5_000_000)
    r.add_argument("--per-chunk")
    r.add_argument("--disk-a")
    r.add_argument("--read", action="append", default=[])
    r.add_argument("--stop-if", action="append", default=[])
    r.add_argument("--stop-if-changed", action="append", default=[])
    r.add_argument("--dll", default=DLL)
    p = sub.add_parser("report")
    p.add_argument("--range", nargs=2, required=True, metavar=("LO", "HI"))
    p.add_argument("--group", action="append", required=True, metavar="NAME=DIR_OR_GLOB")
    p.add_argument("--sym", action="append", default=[])
    p.add_argument("--base")
    p.add_argument("--gap", type=int, default=16)
    p.add_argument("--min", type=int, default=8)
    p.add_argument("--top", type=int, default=60)
    p.add_argument("--json")
    a = ap.parse_args()
    cmd_run(a) if a.cmd == "run" else cmd_report(a)


if __name__ == "__main__":
    main()
