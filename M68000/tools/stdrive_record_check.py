"""Check of stdrive's recordings to disk (tools/stdrive.py, "Recordings") and provenance.py --recording.

    python3 tools/stdrive_record_check.py <out dir> [--dll <stserver.dll>]

1. Impossamole's boss fight `py/boss/boss_stdrive.py --delay 700000 --record <out>/rec` from
   `agents/unpoked/hop4s/none/shop/seg5_pit_exit.snap`: the end snapshot must still be byte-identical to
   `pass108/boss/kill_d700000_end.snap` (recording does not perturb the drive), and it leaves one segment.
2. `provenance.py --recording <segment>` in a fresh process slices the boss hit points `$1a645` at the end.
3. The REPL replays the same fight (`pass108/boss/kill_d700000.repl`) with `watch 1a645 1`; every link of the slice
   on `$1a645` must be a REPL WATCH line with the same step, PC and value, and the links must be the REPL's last writes
   in order (none skipped).
Run from M68000/ (the repo root is found by walking up to tools/rdis.py).
"""
import argparse, filecmp, json, os, re, subprocess, sys

ROOT = os.path.dirname(os.path.abspath(__file__))
while not os.path.exists(os.path.join(ROOT, 'tools', 'rdis.py')):
    ROOT = os.path.dirname(ROOT)
ap = argparse.ArgumentParser()
ap.add_argument('out')
ap.add_argument('--dll', default=os.path.join(ROOT, 'server', 'bin', 'Debug', 'net8.0', 'stserver.dll'))
a = ap.parse_args()
out = os.path.abspath(a.out)
os.makedirs(out, exist_ok=True)
IMP = os.path.join(ROOT, 'scratchpad', 'impossamole')
START = os.path.join(IMP, 'agents/unpoked/hop4s/none/shop/seg5_pit_exit.snap')
DISK = os.path.join(IMP, 'impossamole cr replicants - emotion cr replicants.st')
REF = os.path.join(IMP, 'pass108/boss/kill_d700000_end.snap')
REPL = os.path.join(IMP, 'pass108/boss/kill_d700000.repl')
HP = 0x1a645
results = []

def check(name, ok, detail=''):
    results.append(ok)
    print(f'{"PASS" if ok else "FAIL"}  {name}  {detail}', flush=True)

rec = os.path.join(out, 'rec')
if os.path.exists(rec):
    sys.exit(f'{rec} exists: give an empty output directory')
subprocess.run([sys.executable, os.path.join(ROOT, 'reversing/impossamole/py/boss/boss_stdrive.py'), START, '--delay', '700000',
                '--out-dir', out, '--tag', 'rec', '--record', rec, '--dll', a.dll], cwd=ROOT, check=True,
               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
segs = json.load(open(os.path.join(rec, 'segments.json')))
check('1 recorded drive ends byte-identical to kill_d700000_end.snap',
      filecmp.cmp(os.path.join(out, 'rec_end.snap'), REF, shallow=False), f'{len(segs)} segment(s), steps {segs[-1]["base"]}..{segs[-1]["end"]}')

pj = os.path.join(out, 'slice.json')
subprocess.run([sys.executable, os.path.join(ROOT, 'tools/provenance.py'), '--recording', segs[-1]['dir'], a.dll, f'{HP:x}', 'end',
                '--json', pj], cwd=ROOT, check=True, stdout=open(os.path.join(out, 'slice.txt'), 'w'), stderr=subprocess.DEVNULL)
links = []
def walk(n):
    if n.get('kind') == 'mem' and n.get('lo') == HP and 'step' in n:
        links.append((n['step'], n['pc'], n['value']))
    for c in n.get('children', []):
        walk(c)
walk(json.load(open(pj)))
check('2 the slice from the loaded segment has links on $1a645', len(links) > 0, f'{len(links)} links')

script = os.path.join(out, 'watch.repl')
with open(script, 'w') as f:
    f.write(f'watch {HP:x} 1\n')
    for l in open(REPL):
        if not l.startswith(('snap ', 'q')):
            f.write(l)
    f.write(f'snap {os.path.join(out, "repl_end.snap")}\nq\n')
p = subprocess.run(['dotnet', 'exec', os.path.join(ROOT, 'bin/Debug/net8.0/M68000.dll'), 'resume', START, 'repl', '--disk-a', DISK],
                   cwd=ROOT, env=dict(os.environ, ATARI_NOTRACE='1'), stdin=open(script), capture_output=True, text=True)
w = [(int(s), int(pc, 16), int(v, 16)) for s, pc, v in
     re.findall(r'WATCH: step=(\d+) pc=\$([0-9a-f]+) WriteByte \$0001a645 <- \$([0-9a-f]+)', p.stdout + p.stderr)]
check('3a REPL replay ends at the same state', filecmp.cmp(os.path.join(out, 'repl_end.snap'), REF, shallow=False),
      f'{len(w)} WATCH lines')
ws = set(w)
match = sum(l in ws for l in links)
check('3b every slice link is a REPL WATCH line (step, pc, value)', match == len(links), f'{match}/{len(links)}')
check('3c the links are the REPL\'s last writes, none skipped', sorted(links) == w[-len(links):] if links else False)
print(f'{sum(results)}/{len(results)} PASS')
sys.exit(0 if all(results) else 1)
