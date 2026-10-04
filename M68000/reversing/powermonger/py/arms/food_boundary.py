"""food_boundary.py <snap-at-$661a> (PowerMonger 148th, agent A)

The food fallback's compare, on the real 68000: from a snapshot stopped at `$661a` (a natural decision of the commander
with `A1` the group, `D7` its word offset), compute the `$68ee` score with the model (`cmdai_ref.call_68fe/call_68ee`), then for
food = score - 1, score, score + 1, 0 and the natural food poke the group's food `112(A1)` (a longword write that keeps the neighbouring
word) and run `hits 4000 6638 66a4 664c 66b0` from the stop: `$66a4` must fire exactly when food < score (signed `bgt`).
Needs the REPL registers: A1 and D7 are passed as arguments (read them from a `bp 661a` stop).
    python food_boundary.py <snap> <A1 hex> <D7>
"""
import os, subprocess, sys, re
from pathlib import Path
def _root():
    if os.environ.get('M68000_ROOT'): return Path(os.environ['M68000_ROOT'])
    for p in Path(__file__).resolve().parents:
        if (p / 'tools' / 'pm_fsm_ref.py').exists(): return p
ROOT = _root()
sys.path.insert(0, str(ROOT / 'tools')); sys.path.insert(0, str(ROOT / 'reversing/powermonger/py/cmdai'))
import pm_fsm_ref as P, cmdai_ref as C
from disassemble import ram_from_snap
snap, A1, D7 = sys.argv[1], int(sys.argv[2], 16), int(sys.argv[3])
ram = ram_from_snap(snap); m = P.Mem(ram)
A2 = (C.OBJ + C.sp16(m.wu(A1 + 64))) & 0xfffff
men = C.s16(m.wu(A1 + 52))
D3, A3, z = C.call_68fe(m, A1, A2, men - 4)
assert not z, 'no target'
score = C.s16(C.call_68ee(men - 4, D3))
food0 = C.s16(m.wu(A1 + 112))
print('men', men, 'd', D3, 'score', score, 'natural food', food0)
neighbour = m.wu(A1 + 114)
ok = 0
cases = [score - 1, score, score + 1, 0, food0]
for f in cases:
    cmds = ['disk scratchpad/powermonger.st', 'w %x %04x%04x' % (A1 + 112, f & 0xffff, neighbour), 'hits 4000 6638 66a4 664c 66b0 6822', 'q']
    out = subprocess.run(['dotnet', 'exec', 'bin/Debug/net8.0/M68000.dll', 'resume', snap, 'repl'], input='\n'.join(cmds) + '\n', capture_output=True, text=True,
                         cwd=ROOT, env=dict(os.environ, ATARI_NOTRACE='1')).stdout
    h = {a: int(n) for a, n in re.findall(r'\$0*([0-9a-f]+)\s+(\d+)\s+first', out)}
    expect_food = f < score
    got = h.get('66a4', 0) > 0
    good = (got == expect_food) and (h.get('6638', 0) > 0) == (not expect_food)
    ok += good
    print('food %6d: 6638=%d 66a4=%d 66b0=%d  expect %s -> %s' % (f, h.get('6638', 0), h.get('66a4', 0), h.get('66b0', 0), '66a4' if expect_food else '6638', 'OK' if good else 'MISMATCH'))
print('match %d/%d' % (ok, len(cases)))
