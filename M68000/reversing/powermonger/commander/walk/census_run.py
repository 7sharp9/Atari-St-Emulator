"""census_run.py - run the game from every snapshot of the 206 disagreeing pairs with a watch over the men's records.

For each snapshot, the disagreeing men are grouped into watch spans of at most SPAN records; each span is one REPL
run: `m` of every record of the span (the start state), `watch <lo> <len>`, `s <steps>`.
Steps: (1.5 * the model's latest arrival tick + 200) ticks of TICK steps, capped at 3000 ticks.
Outputs under runs/<snapstem>_<lo>.{txt,out,err}. Skips a run whose .out already ends with the final `m` line.

Usage (from M68000/): census_run.py bc_full.json [PAR]
"""
import json
import os
import subprocess
import sys
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
import os as _os
WORK = next(p for p in HERE.parents if (p / 'tools' / 'rdis.py').exists()) / _os.environ.get('CMD_WORK', 'scratchpad/cmd1') / 'walk'
WORK.mkdir(parents=True, exist_ok=True)
ROOT = next(p for p in HERE.parents if (p / 'tools' / 'rdis.py').exists())
SPAN, TICK, BASE = 20, 180000, 0x51b66


def jobs(d):
    sp = defaultdict(list)
    for x in d:
        if x['cls'] == 'b' and x['arrives']:
            sp[x['snap']].append(x)
    out = []
    for snap, xs in sp.items():
        xs.sort(key=lambda x: x['obj'])
        grp = []
        for x in xs:
            if grp and x['obj'] - grp[0]['obj'] >= SPAN:
                out.append((snap, grp))
                grp = []
            grp.append(x)
        out.append((snap, grp))
    return out


def run(job):
    snap, grp = job
    lo, hi = grp[0]['obj'], grp[-1]['obj']
    ticks = min(3000, int(1.5 * max(x['tick'] for x in grp)) + 200)
    stem = '%s_%d' % (Path(snap).stem, lo)
    rd = WORK / os.environ.get('RUNS', 'runs')
    rd.mkdir(exist_ok=True)
    txt, out, err = rd / (stem + '.txt'), rd / (stem + '.out'), rd / (stem + '.err')
    if out.exists() and out.read_text().rstrip().endswith('DONE'):
        return stem, 'cached'
    a0, n = BASE + 50 * lo, 50 * (hi - lo + 1)
    lines = ['disk scratchpad/powermonger.st'] + ['m %x 50' % (BASE + 50 * x['obj']) for x in grp]
    lines += ['watch %x %d' % (a0, n), 's %d' % (ticks * TICK)] + ['m %x 50' % (BASE + 50 * x['obj']) for x in grp]
    lines += ['q']
    txt.write_text('\n'.join(lines) + '\n')
    env = dict(os.environ, ATARI_NOTRACE='1')
    with open(txt) as fi, open(out, 'w') as fo, open(err, 'w') as fe:
        subprocess.run(['dotnet', 'exec', 'bin/Debug/net8.0/M68000.dll', 'resume', snap, 'repl'], stdin=fi, stdout=fo,
                       stderr=fe, cwd=ROOT, env=env)
    with open(out, 'a') as fo:
        fo.write('DONE\n')
    return stem, ticks


if __name__ == '__main__':
    d = json.load(open(sys.argv[1]))
    par = int(sys.argv[2]) if len(sys.argv) > 2 else 4
    js = jobs(d)
    print(len(js), 'runs', flush=True)
    with ThreadPoolExecutor(par) as ex:
        for r in ex.map(run, js):
            print(*r, flush=True)
