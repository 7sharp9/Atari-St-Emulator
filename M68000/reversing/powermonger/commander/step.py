"""step.py <in.snap> <out.snap> <steps> [order.json] [--hits a,b,..] [--watch addr len] [--quiet]
One harness step: write a REPL script (disk line, act.py pokes for the order JSON, optional watch, `s <steps>` or
`hits <steps> <addrs>`, `snap <out>`, `q`), run the emulator on it, print observe.py's JSON of <out.snap> to stdout and
the wall clock (and per 10M steps) to stderr. The script and the emulator's stdout/stderr are kept next to <out.snap>
as <out>.repl/.out/.err. order.json: see act.from_json (a dict or a list: take / select / order).
Run from anywhere; paths are resolved against M68000/ (found by walking up to tools/rdis.py)."""
import json, os, subprocess, sys, time
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = next(d for d in HERE.parents if (d / 'tools' / 'rdis.py').exists())
sys.path.insert(0, str(HERE))
from observe import observe, load
from act import from_json


def step(insnap, outsnap, steps, actions=None, hits=None, watch=None):
    insnap, outsnap = (ROOT / insnap).resolve(), (ROOT / outsnap).resolve()
    outsnap.parent.mkdir(parents=True, exist_ok=True)
    lines = ['disk scratchpad/powermonger.st']
    if actions: lines += from_json(load(insnap), actions)
    if watch: lines.append(f'watch {watch[0]} {watch[1]}')
    lines.append(f'hits {steps} {" ".join(hits)}' if hits else f's {steps}')
    lines += [f'snap {outsnap}', 'q']
    stem = outsnap.with_suffix('')
    Path(f'{stem}.repl').write_text('\n'.join(lines) + '\n')
    t = time.time()
    with open(f'{stem}.repl') as i, open(f'{stem}.out', 'w') as o, open(f'{stem}.err', 'w') as e:
        subprocess.run(['dotnet', 'exec', str(ROOT / 'bin/Debug/net8.0/M68000.dll'), 'resume', str(insnap), 'repl'],
                       stdin=i, stdout=o, stderr=e, cwd=ROOT, env=dict(os.environ, ATARI_NOTRACE='1'), check=True)
    dt = time.time() - t
    if not outsnap.exists(): sys.exit(f'no snapshot written: see {stem}.out / .err')
    return observe(load(outsnap)), dt


if __name__ == '__main__':
    a = sys.argv[1:]
    hits = watch = None; quiet = '--quiet' in a
    if quiet: a.remove('--quiet')
    if '--hits' in a: i = a.index('--hits'); hits = a[i + 1].split(','); del a[i:i + 2]
    if '--watch' in a: i = a.index('--watch'); watch = a[i + 1:i + 3]; del a[i:i + 3]
    insnap, outsnap, steps = a[0], a[1], int(a[2])
    actions = json.loads(Path(a[3]).read_text()) if len(a) > 3 else None
    obs, dt = step(insnap, outsnap, steps, actions, hits, watch)
    print(f'wall {dt:.1f} s for {steps} steps, {dt * 1e7 / steps:.1f} s per 10M', file=sys.stderr)
    if not quiet: print(json.dumps(obs, indent=1))
