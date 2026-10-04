"""gate_nat_arms.py  (PowerMonger 148th, agent A)

Natural `$6522` entries that contain an arm no earlier gate had a natural state for: the model (`cmdai_ref.call_6522`) against `callcap 6522`
on the real 68000, every byte of RAM except the stack (same comparison as gate_cmdai.py nat).  Each entry is the snapshot at the `$6522` entry of
the tick whose pass reaches the arm (found with `hits` up to the arm's own hit, then `bpc 6522 N`).  Cases (snapshot, steps to the arm hit, arm address):
  k25  $668c  (transfer, order $04)     L2G_k25_c1   63678190
  k8   $668c                            L2G_k8_c1    72484631
  k143 $666c  (get men behind an enemy) L2G_k143_c3  45152624
  k106 $668c  (24-man captain group, own lords with 17/5/2 men at home, the one enemy lord has 33)  M2G_k106_c1  95761881 (run_arms2.sh batch)
Run after run_arms.sh produced the chunk snapshots.   cd M68000 && .venv/bin/python reversing/powermonger/py/arms/gate_nat_arms.py   (ARMS_WORK env: where batch1/batch2 wrote long/, default scratchpad/pm148/arms)
"""
import json, os, re, subprocess, sys
from pathlib import Path
def _root():
    if os.environ.get('M68000_ROOT'): return Path(os.environ['M68000_ROOT'])
    for p in Path(__file__).resolve().parents:
        if (p / 'tools' / 'pm_fsm_ref.py').exists(): return p
ROOT = _root()
WORK = os.environ.get('ARMS_WORK', 'scratchpad/pm148/arms')
sys.path.insert(0, str(ROOT / 'tools')); sys.path.insert(0, str(ROOT / 'reversing/powermonger/py/cmdai'))
import pm_fsm_ref as P, cmdai_ref as C
from disassemble import ram_from_snap
OUT = ROOT / WORK / 'natgate'; OUT.mkdir(parents=True, exist_ok=True)
CASES = [('k25', 'L2G_k25_c1', 63678190, '668c'), ('k8', 'L2G_k8_c1', 72484631, '668c'), ('k143', 'L2G_k143_c3', 45152624, '666c'),
         ('k106', 'M2G_k106_c1', 95761881, '668c')]
def repl(snap, cmds):
    return subprocess.run(['dotnet', 'exec', 'bin/Debug/net8.0/M68000.dll', 'resume', str(snap), 'repl'], input='\n'.join(cmds) + '\nq\n', capture_output=True, text=True,
                          cwd=ROOT, env=dict(os.environ, ATARI_NOTRACE='1')).stdout
ok_states = 0; tot_bytes = 0; ok_bytes = 0
for name, chunk, steps, arm in CASES:
    snap = f'{WORK}/long/{chunk}.snap'
    out = repl(snap, ['disk scratchpad/powermonger.st', f'hits {steps + 10} 6522 {arm}'])
    h = {a: int(n) for a, n in re.findall(r'\$0*([0-9a-f]+)\s+(\d+)\s+first', out)}
    n = h['6522']                                   # the last $6522 entry before the arm hit (the arm hit is inside that call)
    assert h[arm] == 1 or name == 'k143', h
    ent = OUT / f'{name}_{arm}_entry.snap'
    repl(snap, ['disk scratchpad/powermonger.st', f'bpc 6522 {n} {steps + 1000}', f'snap {ent.relative_to(ROOT)}'])
    j = OUT / f'{name}_{arm}.json'
    j.unlink(missing_ok=True)
    repl(ent.relative_to(ROOT), ['disk scratchpad/powermonger.st', f'callcap 6522 3000000 {j.relative_to(ROOT)}'])
    jj = json.load(open(j))
    if jj.get('outcome') != 'returned':
        print(name, 'callcap outcome', jj.get('outcome')); continue
    ram0 = ram_from_snap(str(ent)); P.init_tables(ram0)
    m = P.Mem(ram0); C.TRACE.clear(); C.call_6522(m)
    sp = jj['entrySP']
    real = {a: b1 for a, b0, b1 in jj['mem'] if not sp - 0x300 <= a < sp}
    model = {a: m.r[a] for a in range(len(ram0)) if m.r[a] != ram0[a] and not sp - 0x300 <= a < sp}
    keys = set(real) | set(model)
    bad = [a for a in keys if real.get(a, ram0[a]) != model.get(a, ram0[a])]
    tot_bytes += len(keys); ok_bytes += len(keys) - len(bad); ok_states += not bad
    print('%-5s arm $%s: model arms %s, changed bytes %d, mismatching %d %s' % (name, arm, sorted(set(C.TRACE)), len(keys), len(bad), [(hex(a), real.get(a, ram0[a]), model.get(a, ram0[a])) for a in sorted(bad)[:5]]))
print('natural states identical: %d/%d, bytes %d/%d' % (ok_states, len(CASES), ok_bytes, tot_bytes))
