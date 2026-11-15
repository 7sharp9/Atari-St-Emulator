"""Canyon flight gate (README "Canyon flight"). Run from anywhere:  uv run python reversing/captainblood/py/canyon/gate.py
1. Captures canyon/main_loop.snap fresh (canyon_1.snap + 1.5M steps; the old file is deleted first).
2. gate_collision.py: the collision predicate at $10c24 against the emulator (52/52 D0 and branch; three broken
   controls are printed too and must fail).
3. routes.py esc and routes.py control from q16_d.snap: `hits` on $d8c8 over the same 18.2M steps after the "land"
   click, with and without ESC held in flight. The ROUTE line is built from what each arm actually measured, so
   swapped arms print `esc d8c8=0`."""
import os, re, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from repl import Repl, ROOT
OUT = os.path.join(ROOT, 'scratchpad/captainblood/canyon')
os.makedirs(OUT, exist_ok=True)
ml = os.path.join(OUT, 'main_loop.snap')
for p in (ml, ml + '.prov.json'):
    if os.path.exists(p): os.remove(p)
r = Repl('scratchpad/captainblood/canyon_1.snap'); r.step(1500000); r.snap('scratchpad/captainblood/canyon/main_loop.snap'); r.close()
assert os.path.exists(ml), 'main_loop.snap not written'
py = sys.executable
def run(*a):
    p = subprocess.run([py, os.path.join(HERE, a[0]), *a[1:]], cwd=ROOT, capture_output=True, text=True)
    if p.returncode: sys.exit(f'{a} failed: {p.stderr[-400:]}')
    return p.stdout
print(run('gate_collision.py', '40', '12'), end='')
res = {}
for arm in ('esc', 'control'):
    out = run('routes.py', arm)
    line = [l for l in out.splitlines() if l.startswith(arm + ' {')][0]
    res[arm] = (int(re.search(r"'\$00d8c8': (\d+)", line).group(1)), re.search(r'hit table (0x[0-9a-f]+)', line).group(1))
    print(line)
print(f"ROUTE esc d8c8={res['esc'][0]} table={res['esc'][1]} control d8c8={res['control'][0]} table={res['control'][1]}")
