"""Snapshot recipes: rebuild an anchor snapshot from a cold boot, byte for byte, through the stdin REPL.

    uv run python tools/recipe.py build  <recipe.json> <out.snap>  [--dll D] [--disk-path P] [--work W]
    uv run python tools/recipe.py verify <recipe.json> [<reference.snap>] [--dll D] [--disk-path P] [--work W]
    uv run python tools/recipe.py list   <dir>

Run from `M68000/` (the ROM `TOS100UK.IMG` is found from the cwd). Every `dotnet exec` gets ATARI_NOTRACE=1.

A recipe is one JSON file (paths in it are relative to the recipe file, except `reference`):

    {
      "format": 1,
      "name": "c_s30",
      "disk": {"file": "carrier_auto.st", "sha256": "<hex>"},   # found through the disk search path, checked by hash
      "parent": "c80.json",           # another recipe, or null for a cold boot
      "boot_steps": 80000000,         # cold boot only: steps before the script (or before the save if no script)
      "repl": "../drive.txt",         # optional REPL script; `snap <out>` is appended. null = no script
      "repl_sha256": "<hex>",         # the script as recorded; a different script is INPUT_CHANGED
      "expect": {"sha256": "<hex>", "step": 170918000,
                 "dll_path": "bin/Debug/net8.0/M68000.dll", "dll_sha256": "<hex>"},
      "reference": "carrier/c_s30.snap"   # optional, relative to the disk search path's first entry (scratchpad)
    }

How each node is built (the same argv the original lineages used, so the original snapshots are the reference):
  cold, no script:   <boot_steps> snapshot <out> --disk-a <disk>
  cold, script:      <boot_steps> repl --disk-a <disk>  < script + "snap <out>"
  child:             resume <parent.snap> repl --disk-a <disk>  < script + "snap <out>"
A child's parent is rebuilt first, recursively, so every build starts from a cold boot. Before each node the output
file and its sidecar are deleted, and the exit code, the file's existence and the sidecar's step are checked, so a
failed build cannot leave an old file that compares equal.

Disk search path: `--disk-path` or `$ST_DISK_PATH` (os.pathsep-separated), default `M68000/scratchpad`. A directory
is searched for `<file>` directly and one level down; the candidate whose SHA-256 matches is used.

Outcomes (printed as `OUTCOME <name>`, exit code in brackets; `build` gives all but NONDETERMINISTIC, judged on
the leaf's recorded hash alone; both print the sha256 of the DLL they ran):
  MATCH (0)              both builds identical to each other, to expect.sha256 and to the reference, same DLL
  MATCH_OTHER_DLL (0)    the same, but the running DLL is not the recorded one (the recipe still holds on it)
  DLL_MISMATCH (3)       bytes differ from the recorded hash and the running DLL is not the one that recorded it:
                         rebuild-and-record question, not a recipe or determinism failure
  DIFFERS (1)            bytes differ from the recorded hash or the reference with the recorded DLL
  NONDETERMINISTIC (4)   the two builds differ from each other
  INPUT_CHANGED (5)      disk or script hash differs from the recipe's
  BUILD_FAILED (6)       a dotnet exec failed, wrote no file, or stopped at another step

Not supported: stdrive / stserver journals (the anchors here are REPL lineages, and stserver's DLL is built
separately from bin/), environment-scheduled input (ATARI_KEY_INPUT), live window input, and recipes whose parent
uses another disk image (a `disk` REPL line inside a script is allowed: its path is whatever the script says).
"""
import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time

M68K = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_DLL = os.path.join(M68K, 'bin', 'Debug', 'net8.0', 'M68000.dll')

EXIT = {'MATCH': 0, 'MATCH_OTHER_DLL': 0, 'DIFFERS': 1, 'DLL_MISMATCH': 3, 'NONDETERMINISTIC': 4,
        'INPUT_CHANGED': 5, 'BUILD_FAILED': 6}


class Fail(Exception):
    def __init__(self, outcome, msg):
        super().__init__(msg)
        self.outcome = outcome


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def load_recipe(path):
    path = os.path.abspath(path)
    with open(path) as f:
        r = json.load(f)
    if r.get('format') != 1:
        raise Fail('BUILD_FAILED', f'{path}: not a format-1 recipe')
    r['_path'] = path
    r['_dir'] = os.path.dirname(path)
    return r


def search_path(arg):
    s = arg or os.environ.get('ST_DISK_PATH') or os.path.join(M68K, 'scratchpad')
    return [os.path.abspath(p) for p in s.split(os.pathsep) if p]


def find_disk(disk, dirs):
    name, want = disk['file'], disk['sha256']
    seen = []
    for d in dirs:
        cands = [os.path.join(d, name)]
        try:
            cands += [os.path.join(d, e, name) for e in sorted(os.listdir(d))]
        except OSError:
            continue
        for c in cands:
            if os.path.isfile(c):
                h = sha256(c)
                if h == want:
                    return c
                seen.append((c, h))
    detail = '; '.join(f'{c} sha256 {h}' for c, h in seen) or 'no file of that name'
    raise Fail('INPUT_CHANGED', f'disk {name} sha256 {want} not found in {dirs}: {detail}')


def chain(recipe):
    """[root, ..., recipe] following parents."""
    out, r = [], recipe
    while r is not None:
        out.append(r)
        if len(out) > 64:
            raise Fail('BUILD_FAILED', 'parent chain longer than 64: a cycle?')
        r = load_recipe(os.path.join(r['_dir'], r['parent'])) if r.get('parent') else None
    return out[::-1]


def run_node(r, out, parent_snap, dll, dirs, log):
    disk = find_disk(r['disk'], dirs)
    script = None
    if r.get('repl'):
        sp = os.path.join(r['_dir'], r['repl'])
        h = sha256(sp)
        if r.get('repl_sha256') and h != r['repl_sha256']:
            raise Fail('INPUT_CHANGED', f'{r["name"]}: script {sp} sha256 {h}, recipe records {r["repl_sha256"]}')
        with open(sp) as f:
            lines = [ln for ln in f.read().splitlines()]
        # a trailing `q` or `snap` would end the drive before our save: refuse instead of guessing
        tail = [ln.strip() for ln in lines if ln.strip() and not ln.strip().startswith('#')]
        if tail and tail[-1] in ('q', 'quit'):
            raise Fail('BUILD_FAILED', f'{sp} ends with q: recipe scripts must leave the save to recipe.py')
        script = '\n'.join(lines + [f'snap {out}', 'q']) + '\n'
    if parent_snap is None:
        n = str(int(r['boot_steps']))
        argv = [n, 'snapshot', out] if script is None else [n, 'repl']
    else:
        if script is None:
            raise Fail('BUILD_FAILED', f'{r["name"]}: a child recipe needs a repl script')
        argv = ['resume', parent_snap, 'repl']
    argv += ['--disk-a', disk]
    for p in (out, out + '.prov.json'):
        if os.path.exists(p):
            os.remove(p)
    env = dict(os.environ, ATARI_NOTRACE='1')
    t0 = time.time()
    with open(log, 'w') as lf:
        p = subprocess.run(['dotnet', 'exec', dll] + argv, cwd=M68K, env=env, input=script, text=True,
                           stdout=lf, stderr=subprocess.STDOUT)
    wall = time.time() - t0
    if p.returncode != 0:
        raise Fail('BUILD_FAILED', f'{r["name"]}: exit {p.returncode} (log {log})')
    if not os.path.isfile(out):
        raise Fail('BUILD_FAILED', f'{r["name"]}: exit 0 but no {out} (log {log})')
    step = None
    try:
        with open(out + '.prov.json') as f:
            step = json.load(f).get('step')
    except (OSError, ValueError):
        pass
    want = r.get('expect', {}).get('step')
    if want is not None and step != want:
        raise Fail('BUILD_FAILED', f'{r["name"]}: stopped at step {step}, recipe records {want} (log {log})')
    h = sha256(out)
    print(f'  built {r["name"]}: step {step} sha256 {h} wall {wall:.1f}s  argv {" ".join(argv[:3])}')
    return h, step, wall


def build(recipe_path, out, dll, dirs, work):
    """Build the chain into work/, the leaf to out. Returns [(recipe, sha256, step)] root first."""
    out = os.path.abspath(out)
    leaf = load_recipe(recipe_path)
    nodes = chain(leaf)
    os.makedirs(work, exist_ok=True)
    res, parent = [], None
    for r in nodes:
        dst = out if r is nodes[-1] else os.path.join(work, r['name'] + '.snap')
        h, step, _ = run_node(r, dst, parent, dll, dirs, os.path.join(work, r['name'] + '.log'))
        res.append((r, h, step))
        parent = dst
    return res


def cmp_print(a, b):
    p = subprocess.run(['cmp', a, b], capture_output=True, text=True)
    line = (p.stdout + p.stderr).strip() or 'identical'
    print(f'  cmp {a} {b}: {line} (exit {p.returncode})')
    return p.returncode == 0


def verify(recipe_path, reference, dll, dirs, work):
    dll_h = sha256(dll)
    leaf = load_recipe(recipe_path)
    rec_dll = leaf.get('expect', {}).get('dll_sha256')
    print(f'DLL {dll} sha256 {dll_h}')
    print(f'recipe {leaf["_path"]} records dll_sha256 {rec_dll}'
          + ('' if rec_dll == dll_h else '  (DIFFERENT DLL)'))
    os.makedirs(work, exist_ok=True)
    tmp = tempfile.mkdtemp(prefix='verify_', dir=work)
    builds = []
    for i in (1, 2):
        print(f'build {i}:')
        out = os.path.join(tmp, f'b{i}', leaf['name'] + '.snap')
        builds.append((out, build(recipe_path, out, dll, dirs, os.path.join(tmp, f'b{i}'))))
    (o1, r1), (o2, r2) = builds
    ok_det = cmp_print(o1, o2)
    for (r, h1, _), (_, h2, _) in zip(r1, r2):
        if h1 != h2:
            print(f'  node {r["name"]}: build 1 {h1} build 2 {h2}')
            ok_det = False
    ok_exp = True
    for r, h, _ in r1:
        e = r.get('expect', {}).get('sha256')
        same = (e == h)
        ok_exp &= same
        print(f'  node {r["name"]}: built {h} recorded {e} {"equal" if same else "DIFFERENT"}')
    ref = reference or (os.path.join(dirs[0], leaf['reference']) if leaf.get('reference') else None)
    ok_ref = True
    if ref:
        if os.path.isfile(ref):
            ok_ref = cmp_print(ref, o1)
        else:
            print(f'  reference {ref} not present: compared against the recorded hash only')
    if not ok_det:
        return 'NONDETERMINISTIC'
    if ok_exp and ok_ref:
        return 'MATCH' if rec_dll == dll_h else 'MATCH_OTHER_DLL'
    return 'DLL_MISMATCH' if rec_dll != dll_h else 'DIFFERS'


def list_dir(d):
    rows = []
    for root, _, files in os.walk(d):
        for f in sorted(files):
            if not f.endswith('.json'):
                continue
            p = os.path.join(root, f)
            try:
                r = load_recipe(p)
            except (Fail, ValueError, OSError):
                continue
            e = r.get('expect', {})
            rows.append((os.path.relpath(p, d), r['name'], r.get('parent') or 'cold boot',
                         r['disk']['file'], e.get('step'), (e.get('sha256') or '')[:16],
                         (e.get('dll_sha256') or '')[:16]))
    for row in rows:
        print('  '.join(str(x) for x in row))
    if not rows:
        print(f'no recipes under {d}')


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    sub = ap.add_subparsers(dest='cmd', required=True)
    for name in ('build', 'verify'):
        s = sub.add_parser(name)
        s.add_argument('recipe')
        s.add_argument('snap', nargs='?' if name == 'verify' else None)
        s.add_argument('--dll', default=DEFAULT_DLL)
        s.add_argument('--disk-path')
        s.add_argument('--work', help='work dir (default: a temp dir under scratchpad/recipes)')
    sub.add_parser('list').add_argument('dir')
    a = ap.parse_args()
    if a.cmd == 'list':
        list_dir(a.dir)
        return 0
    dirs = search_path(a.disk_path)
    dll = os.path.abspath(a.dll)
    work = os.path.abspath(a.work or os.path.join(M68K, 'scratchpad', 'recipes'))
    t0 = time.time()
    try:
        if a.cmd == 'build':
            dll_h = sha256(dll)
            print(f'DLL {dll} sha256 {dll_h}')
            res = build(a.recipe, a.snap, dll, dirs, tempfile.mkdtemp(prefix='build_', dir=_mk(work)))
            r, h, _ = res[-1]
            e = r.get('expect', {}).get('sha256')
            rec_dll = r.get('expect', {}).get('dll_sha256')
            print(f'{a.snap} sha256 {h} recorded {e} {"equal" if h == e else "DIFFERENT"}')
            if e is None or h == e:
                outcome = 'MATCH' if rec_dll in (None, dll_h) else 'MATCH_OTHER_DLL'
            else:
                outcome = 'DLL_MISMATCH' if rec_dll != dll_h else 'DIFFERS'
            print(f'OUTCOME {outcome}')
            return EXIT[outcome]
        outcome = verify(a.recipe, a.snap, dll, dirs, work)
    except Fail as f:
        print(f'  {f}')
        outcome = f.outcome
        if a.cmd == 'build':
            print(f'OUTCOME {outcome}')
            return EXIT[outcome]
    print(f'OUTCOME {outcome}  (wall {time.time() - t0:.1f}s)')
    return EXIT[outcome]


def _mk(d):
    os.makedirs(d, exist_ok=True)
    return d


if __name__ == '__main__':
    sys.exit(main())
