"""Re-run a game's promoted callcap gates and report every match count that moved.

    uv run python tools/gates.py list <game|all>
    uv run python tools/gates.py run <game|all> [-k substr] [-j N] [--root M68000_DIR] [--dry-run]

Each game lists its gates in `reversing/<game>/gates.toml`:

    [[gate]]
    name = "dbde"                          # unique within the game
    cmd = "{python} gate_dbde.py 2500 11"  # {python}: M68000/.venv's interpreter; {root}: the M68000 dir
    cwd = "py/ai"                          # relative to reversing/<game>/ (default: M68000/)
    expect = ["2500/2500"]                 # the counts the docs record, as printed (spaces around / ignored);
                                           # "re:<regex>" for a script that prints no a/b (searched in the output)
    cite = "ai.md section 13"              # where the docs record them
    minutes = 5                            # rough runtime; the timeout is max(10, 4 * minutes) minutes

A count goes in `expect` only when a doc records it for exactly this command line: no invented counts. A gate passes
when every expected `a/b` (or `re:` pattern) appears in its output; otherwise it is CHANGED (with the counts it did print) or ERROR (no
count, a non-zero exit with no count, a timeout, or an `expect` entry that is neither: a bare word is never matched,
so a gate's PASS line is `"re:(?m)^PASS$"`, since `re.search` runs without MULTILINE). Never put a `reuse` argument in `cmd`: the point is fresh callcaps.
A gate that only reads saved snapshots (Super Sprint's `plane2`, 1 s) runs no emulator and cannot catch an emulator
change: say so in a comment on its entry.

The gates read their corpora from `scratchpad/`, which is per checkout, so `--root` runs them in another checkout's
M68000 dir (its scripts, its scratchpad, its `bin/` DLL; the manifests are always this checkout's). To gate a worktree's
own build, run in the worktree after linking its inputs and cloning the scratchpad (CLAUDE.md "Emulator changes"):
pointing `--root` at the main checkout runs the main checkout's DLL. Logs go to `<root>/scratchpad/gates/<game>/<name>.log` and the summary to `.../last_run.json`.
`expect` is matched as a set: two runs in one gate that print the same count (`42/42` twice) need labelled
`re:` patterns (`"re:takeoff at rest 42/42"`, carriercommand `units`), or one of them can stop printing unnoticed.
Every run sets `ATARI_NOTRACE=1` and `M68000_ROOT=<root>`. The exit status is 1 when any gate did not pass.
The header line and every result in `last_run.json` carry the SHA-256 of `<root>/bin/Debug/net8.0/M68000.dll` and
`<root>/server/bin/Debug/net8.0/stserver.dll` (`dll`, `server_dll`; the first 16 hex digits), hashed before the first
gate and again after the last: a rebuild in between (another session's) marks every result `dll_changed`, since the
run then tested two builds.

Default `-j 1`: gates share the machine with other sessions' runs and some share scratch output dirs.
"""
import argparse
import hashlib
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


def venv_python():
    """This checkout's uv venv interpreter (`M68000/.venv`, made by `uv sync`): gate scripts need its numpy and
    pillow whichever python launched gates.py (the system python3 has neither)."""
    venv = ROOT / ".venv"
    for p in (venv / "bin" / "python", venv / "Scripts" / "python.exe"):
        if p.exists():
            return venv, p
    sys.exit(f"gates.py: no project venv at {venv}; run `cd {ROOT} && uv sync` once (DEVELOPING.md \"Python tooling\")")


def run_one(root, game, gate, dry):
    cwd = root / "reversing" / game / gate["cwd"] if "cwd" in gate else root
    venv, python = venv_python()
    cmd = gate["cmd"].format(python=python, root=root)
    if dry:
        return dict(game=game, name=gate["name"], status="DRY", cmd=cmd, cwd=str(cwd))
    logdir = root / "scratchpad" / "gates" / game
    logdir.mkdir(parents=True, exist_ok=True)
    log = logdir / f"{gate['name']}.log"
    # as `uv run` would: a bare `python` or `uv run` inside a gate's shell script resolves to the same venv
    env = dict(os.environ, ATARI_NOTRACE="1", M68000_ROOT=str(root), VIRTUAL_ENV=str(venv),
               PATH=os.pathsep.join([str(python.parent), os.environ.get("PATH", "")]))
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
    # a bare word such as "PASS" is never in `got` (only a/b counts are): reject it rather than report CHANGED
    bad = [f for f in gate["expect"] if not f.startswith("re:") and not norm(f)]
    if bad:
        status = "ERROR"
        note = f"expect entries neither a/b nor re: {', '.join(bad)} (a word is 're:(?m)^PASS$')"
    elif rc is None:
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


def dll_hashes(root):
    def h(p):
        try:
            return hashlib.sha256(p.read_bytes()).hexdigest()[:16]
        except OSError:
            return None
    return dict(dll=h(root / "bin" / "Debug" / "net8.0" / "M68000.dll"),
                server_dll=h(root / "server" / "bin" / "Debug" / "net8.0" / "stserver.dll"))


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
    venv_python()      # a missing venv stops here, before the header, not inside a worker thread
    dlls = dll_hashes(root)
    print(f"# {len(gates)} gates in {root} at {head(root)}, M68000.dll {dlls['dll']}, stserver.dll {dlls['server_dll']}",
          flush=True)
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
    changed = dll_hashes(root) != dlls
    if changed:
        print(f"# WARNING: a DLL changed during the run ({dlls} -> {dll_hashes(root)}): the gates tested more than one build")
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
        old.update({r["name"]: dict(r, when=when, head=head(root), **dlls, dll_changed=changed) for r in rs})
        f.write_text(json.dumps(dict(when=when, results=list(old.values())), indent=1))
    bad = [r for r in results if r["status"] != "PASS"]
    print(f"# {len(results) - len(bad)}/{len(results)} pass" + (f"; not passing: {', '.join(r['game'] + '/' + r['name'] for r in bad)}" if bad else ""))
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
