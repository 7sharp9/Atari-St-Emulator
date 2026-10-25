"""Re-run a game's promoted callcap gates and report every match count that moved.

    uv run python tools/gates.py list <game|all>
    uv run python tools/gates.py run <game|all> [-k substr] [-j N] [--root M68000_DIR] [--dry-run]

Each game lists its gates in `reversing/<game>/gates.toml`:

    [[gate]]
    name = "dbde"                          # unique within the game
    cmd = "{python} gate_dbde.py 2500 11"  # {python}: this interpreter; {root}: the M68000 dir
    cwd = "py/ai"                          # relative to reversing/<game>/ (default: M68000/)
    expect = ["2500/2500"]                 # the counts the docs record, as printed (spaces around / ignored);
                                           # "re:<regex>" for a script that prints no a/b (searched in the output)
    cite = "ai.md section 13"              # where the docs record them
    minutes = 5                            # rough runtime; the timeout is max(10, 4 * minutes) minutes

A count goes in `expect` only when a doc records it for exactly this command line: no invented counts. A gate passes
when every expected `a/b` (or `re:` pattern) appears in its output; otherwise it is CHANGED (with the counts it did print) or ERROR (no
count, a non-zero exit with no count, a timeout). Never put a `reuse` argument in `cmd`: the point is fresh callcaps.

The gates read their corpora from `scratchpad/`, which is per checkout, so `--root` runs them in another checkout's
M68000 dir (its scripts, its scratchpad, its `bin/` DLL; the manifests are always this checkout's): from a worktree
with an empty scratchpad, point it at the main checkout. Logs go to `<root>/scratchpad/gates/<game>/<name>.log` and the summary to `.../last_run.json`.
Every run sets `ATARI_NOTRACE=1` and `M68000_ROOT=<root>`. The exit status is 1 when any gate did not pass.

Default `-j 1`: gates share the machine with other sessions' runs and some share scratch output dirs.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time
try:
    import tomllib
except ImportError:      # Python 3.10: the uv venv is 3.11+
    sys.exit("gates.py needs Python 3.11+ (tomllib); run it with `uv run python`")
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = next(d for d in Path(__file__).resolve().parents if (d / "tools" / "rdis.py").exists())
FRAC = re.compile(r"(?<![\d.])(\d[\d,]*)\s*/\s*(\d[\d,]*)(?![\d.])")


def norm(s):
    return {f"{a.replace(',', '')}/{b.replace(',', '')}" for a, b in FRAC.findall(s)}


def load(root, which):
    rev = root / "reversing"
    games = sorted(p.parent.name for p in rev.glob("*/gates.toml")) if which == "all" else [which]
    out = []
    for g in games:
        f = rev / g / "gates.toml"
        if not f.exists():
            sys.exit(f"no {f}")
        gates = tomllib.loads(f.read_text())["gate"]
        names = [x["name"] for x in gates]
        dup = {n for n in names if names.count(n) > 1}
        if dup:
            sys.exit(f"{f}: duplicate gate names {sorted(dup)}")
        for x in gates:
            if "reuse" in x["cmd"].split():
                sys.exit(f"{f}: gate {x['name']} passes `reuse`; gates must make fresh callcaps")
            out.append((g, x))
    return out


def run_one(root, game, gate, dry):
    cwd = root / "reversing" / game / gate["cwd"] if "cwd" in gate else root
    cmd = gate["cmd"].format(python=sys.executable, root=root)
    if dry:
        return dict(game=game, name=gate["name"], status="DRY", cmd=cmd, cwd=str(cwd))
    logdir = root / "scratchpad" / "gates" / game
    logdir.mkdir(parents=True, exist_ok=True)
    log = logdir / f"{gate['name']}.log"
    env = dict(os.environ, ATARI_NOTRACE="1", M68000_ROOT=str(root))
    t0 = time.time()
    timeout = 60 * max(10, 4 * gate.get("minutes", 2))
    try:
        p = subprocess.run(cmd, shell=True, cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                           text=True, errors="replace", timeout=timeout)
        out, rc = p.stdout, p.returncode
    except subprocess.TimeoutExpired as e:
        out = (e.stdout or b"").decode(errors="replace") if isinstance(e.stdout, bytes) else (e.stdout or "")
        rc = None
    dt = time.time() - t0
    log.write_text(f"# cwd {cwd}\n# cmd {cmd}\n# exit {rc}  {dt:.0f}s\n{out}")
    got = norm(out)
    want = {f if f.startswith("re:") else f.replace(" ", "") for f in gate["expect"]}
    missing = sorted(f for f in want if not (re.search(f[3:], out) if f.startswith("re:") else f in got))
    if rc is None:
        status = "ERROR"
        note = f"timeout after {timeout // 60} min"
    elif not missing:
        status = "PASS"
        note = "" if rc == 0 else f"exit {rc}"
    elif got:
        status = "CHANGED"
        tail = [f for line in out.splitlines()[-25:] for f in sorted(norm(line))]
        note = f"missing {', '.join(missing)}; printed {', '.join(tail[-6:]) or ', '.join(sorted(got)[:6])}"
    else:
        status = "ERROR"
        note = f"exit {rc}, no a/b count: " + (out.strip().splitlines() or [""])[-1][:160]
    return dict(game=game, name=gate["name"], status=status, note=note, secs=round(dt), exit=rc,
                expect=sorted(want), log=str(log), cmd=cmd, cwd=str(cwd))


def head(root):
    try:
        return subprocess.run(["git", "-C", str(root), "rev-parse", "--short", "HEAD"], capture_output=True,
                              text=True).stdout.strip()
    except OSError:
        return "?"


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("action", choices=["list", "run"])
    ap.add_argument("game", help="a reversing/<game> with a gates.toml, or all")
    ap.add_argument("-k", help="only gates whose name contains this")
    ap.add_argument("-j", type=int, default=1, help="gates run at once (1)")
    ap.add_argument("--root", type=Path, default=ROOT, help="the M68000 dir to run in (default: this checkout's)")
    ap.add_argument("--dry-run", action="store_true", help="print each command and cwd, run nothing")
    a = ap.parse_args()
    root = a.root.resolve()
    gates = [(g, x) for g, x in load(ROOT, a.game) if not a.k or a.k in x["name"]]
    if a.action == "list":
        for g, x in gates:
            print(f"{g:12} {x['name']:16} ~{x.get('minutes', '?')} min  expect {', '.join(x['expect'])}  "
                  f"[{x.get('cwd', '.')}] {x['cmd']}  ({x.get('cite', '')})")
        return
    print(f"# {len(gates)} gates in {root} at {head(root)}", flush=True)
    results = []

    def go(gx):
        r = run_one(root, gx[0], gx[1], a.dry_run)
        print(f"{r['status']:8} {r['game']}/{r['name']}"
              + (f"  {r['secs']}s  {r['note']}" if not a.dry_run else f"  [{r['cwd']}] {r['cmd']}"), flush=True)
        return r

    with ThreadPoolExecutor(max_workers=max(1, a.j)) as ex:
        results = list(ex.map(go, gates))
    if a.dry_run:
        return
    by = {}
    for r in results:
        by.setdefault(r["game"], []).append(r)
    for g, rs in by.items():      # a -k run updates its gates' entries and keeps the others
        f = root / "scratchpad" / "gates" / g / "last_run.json"
        when = time.strftime("%Y-%m-%d %H:%M:%S")
        old = {}
        if f.exists():
            try:
                old = {r["name"]: r for r in json.loads(f.read_text())["results"]}
            except (ValueError, KeyError):      # a corrupt summary is rewritten from this run
                old = {}
        old.update({r["name"]: dict(r, when=when, head=head(root)) for r in rs})
        f.write_text(json.dumps(dict(when=when, results=list(old.values())), indent=1))
    bad = [r for r in results if r["status"] != "PASS"]
    print(f"# {len(results) - len(bad)}/{len(results)} pass" + (f"; not passing: {', '.join(r['game'] + '/' + r['name'] for r in bad)}" if bad else ""))
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
