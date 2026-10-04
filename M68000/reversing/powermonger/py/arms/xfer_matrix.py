"""xfer_matrix.py <snap at $65e0> <A1 hex> <D7>  (PowerMonger 148th, agent A)

The closed-form arm predicate (predicate_check.predict) against the REAL 68000 on one natural decision state (the natural `$668c` of
Play Random Land k25: `bpc 65e0 3` from `L2G_k25_c1.snap`, A1 = $518f0, D7 = 4).  Each case pokes the inputs the predicate names (men word 52(A1),
the own-side lords' and the enemy lords' home troops, word 8 of the lord records; longword writes keep the neighbouring word) and runs
`hits 6000` over the arm entry points; the arm the real code took is compared with the predicted one.  The pokes are for checking the derived
precondition, not for the reaching claim (the reaching claim is the unpoked natural `$668c`).
"""
import os, re, subprocess, sys
from pathlib import Path
def _root():
    if os.environ.get('M68000_ROOT'): return Path(os.environ['M68000_ROOT'])
    for p in Path(__file__).resolve().parents:
        if (p / 'tools' / 'pm_fsm_ref.py').exists(): return p
ROOT = _root()
sys.path.insert(0, str(ROOT / 'tools')); sys.path.insert(0, str(ROOT / 'reversing/powermonger/py/cmdai')); sys.path.insert(0, str(Path(__file__).resolve().parent))
import pm_fsm_ref as P, cmdai_ref as C
from disassemble import ram_from_snap
import predicate_check as PC
snap, A1, D7 = sys.argv[1], int(sys.argv[2], 16), int(sys.argv[3])
ram = ram_from_snap(snap)
m0 = P.Mem(ram)
A2 = (C.OBJ + C.sp16(m0.wu(A1 + 64))) & 0xfffff
own = m0.bu(A2 + 5)
lords = [a for a in range(C.LORDS, C.LORDS_END, 32) if m0.bu(a)]
own_l = [a for a in lords if m0.bu(a) == own]
en_l = [a for a in lords if m0.bu(a) != own]
ARMS = {'65c8': 'getmen', '65f4': 'escort', '6638': 'attack', '66b0': 'food', '666c': 'getmen2', '6686': 'idle_nomen_or_xfer', '668c': 'xfer'}
def words(pokes):
    """pokes: {addr: value} word writes -> REPL longword writes preserving the next word"""
    return ['w %x %04x%04x' % (a, v & 0xffff, m0.wu(a + 2)) for a, v in pokes.items()]
cases = [
    ('natural', {}),
    ('own lord 0 home := 2', {own_l[0] + 8: 2}),
    ('men := 22', {A1 + 52: 22}),
    ('men := 22, all enemy lords home := 30', {A1 + 52: 22, **{a + 8: 30 for a in en_l}}),
    ('men := 0', {A1 + 52: 0}),
    ('own lord 0 home := 2, men := 22, enemy homes := 30', {own_l[0] + 8: 2, A1 + 52: 22, **{a + 8: 30 for a in en_l}}),
    ('men := 5, enemy homes := 1', {A1 + 52: 5, **{a + 8: 1 for a in en_l}}),
    ('men := 5, enemy homes := 0', {A1 + 52: 5, **{a + 8: 0 for a in en_l}}),
    ('men := 25, own lord 0 home := 2, enemy lords home := 26', {A1 + 52: 25, own_l[0] + 8: 2, **{a + 8: 26 for a in en_l}}),
    ('men := 25, own lord 0 home := 2, enemy lords home := 28', {A1 + 52: 25, own_l[0] + 8: 2, **{a + 8: 28 for a in en_l}}),
]
ok = 0
for name, pk in cases:
    m = P.Mem(bytearray(ram))
    for a, v in pk.items(): m.ww(a, v)
    want = PC.predict(m, A1, A2, D7)
    cmds = ['disk scratchpad/powermonger.st'] + words(pk) + ['hits 8000 ' + ' '.join(ARMS) + ' 66c8', 'q']
    out = subprocess.run(['dotnet', 'exec', 'bin/Debug/net8.0/M68000.dll', 'resume', snap, 'repl'], input='\n'.join(cmds) + '\n', capture_output=True, text=True,
                         cwd=ROOT, env=dict(os.environ, ATARI_NOTRACE='1')).stdout
    h = {a: int(n) for a, n in re.findall(r'\$0*([0-9a-f]+)\s+(\d+)\s+first', out)}
    if h.get('65c8'): got = 'getmen'
    elif h.get('65f4'): got = 'escort'
    elif h.get('666c'): got = 'getmen2'
    elif h.get('6638'): got = 'attack'
    elif h.get('66b0'): got = 'food'
    elif h.get('668c'): got = 'xfer'
    elif h.get('6686'): got = 'idle_nomen'
    elif h.get('66c8'): got = 'idle0'
    else: got = 'none'
    good = got == want
    ok += good
    print('%-62s predicted %-10s real %-10s %s' % (name, want, got, 'OK' if good else 'MISMATCH'))
print('match %d/%d' % (ok, len(cases)))
