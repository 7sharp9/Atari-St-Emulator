"""layout_crosscheck.py: tools/layout.py's decode of an Impossamole snapshot against this directory's repl.py decoder.

Two byte sources for slots 6 (hero), 7 (boss) and 16 (swipe) of agents/unpoked/hop4s/none/shop/seg5_pit_exit.snap:
(1) a raw REPL `m` dump right after `resume` (no step), read at repl.py's own `fmt_slot` offsets with its `w`/`sw`;
(2) repl.py's live `Repl` (which steps 1 instruction on start) and its `slot()` helper. Each is compared field by field
with layout.py's decode of the .snap file (13 fields per slot); a negative control puts slot 7's bytes against slot 6.
Expected: 39 match, 0 mismatch twice; the control reports mismatches.
    uv run python reversing/impossamole/py/boss/layout_crosscheck.py      # from M68000/
DATA (default: this checkout's M68000) holds the snapshot, the disk and bin/'s DLL; a worktree points it at the main
checkout. Output: none written (the snapshot is copied to scratchpad/layout/impossamole/).
"""
import os
import shutil
import subprocess
import sys

W = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..'))
MAIN = os.environ.get('DATA', W)
OUT = W + '/scratchpad/layout/impossamole'
os.makedirs(OUT, exist_ok=True)
SNAP = OUT + '/seg5_pit_exit.snap'
shutil.copy(MAIN + '/scratchpad/impossamole/agents/unpoked/hop4s/none/shop/seg5_pit_exit.snap', SNAP)
DISK = MAIN + '/scratchpad/impossamole/impossamole cr replicants - emotion cr replicants.st'
sys.path.insert(0, W + '/tools')
os.environ['M68000_ROOT'] = MAIN                      # repl.py runs DATA's bin/ DLL with cwd DATA (read only)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import layout                                          # noqa: E402
import repl as R                                       # noqa: E402

L = layout.load(W + '/reversing/impossamole/layout.toml')
dec = {v.name: v for v in layout.decode_snap(L, SNAP)}

# repl.py's decoder offsets (fmt_slot): type w0, x sw2, y sw4, v8 sw8, v10 sw10, r b12/b13, f30 w30, b79, b101..b105
REPL_FIELDS = [('type', 0, 'w'), ('x', 2, 'sw'), ('y', 4, 'sw'), ('hit_dx', 8, 'sw'), ('hit_dy', 10, 'sw'),
               ('hit_w', 12, 'b'), ('hit_h', 13, 'b'), ('hitbox_flag', 30, 'w'), ('special_fire', 79, 'b'),
               ('dead', 101, 'b'), ('invuln', 102, 'b'), ('hp', 103, 'b'), ('damage', 104, 'b')]


def rd(b, off, kind):
    return R.w(b, off) if kind == 'w' else R.sw(b, off) if kind == 'sw' else b[off]


def layout_raw(name):
    v = dec[name]
    f = next(f for f in L['arrays'][0]['struct']['fields'] if f['name'] == name.split('.')[-1])
    return v.raw - (1 << 8 * v.width) if f['signed'] and v.raw >> (8 * v.width - 1) else v.raw


def slot_names(n):
    arr = L['arrays'][0] if n < 16 else L['arrays'][1]
    return layout.slot_name(arr, n if n < 16 else n - 16)


def compare(label, slots_bytes):
    ok = bad = 0
    for n, b in slots_bytes.items():
        print(f'-- {label} slot {n}: repl.py fmt_slot: {R.fmt_slot(b)}')
        for fname, off, kind in REPL_FIELDS:
            mine = layout_raw(f'{slot_names(n)}.{fname}')
            theirs = rd(b, off, kind)
            same = mine == theirs
            ok += same; bad += not same
            if not same:
                print(f'   MISMATCH {fname}: layout {mine} repl.py {theirs}')
    print(f'== {label}: {ok} match, {bad} mismatch over {len(slots_bytes)} slots x {len(REPL_FIELDS)} fields')
    return ok, bad


# (1) raw REPL m dump, no step: the whole 20-slot array
env = dict(os.environ, ATARI_NOTRACE='1')
p = subprocess.run(['dotnet', 'exec', MAIN + '/bin/Debug/net8.0/M68000.dll', 'resume', SNAP, 'repl', '--disk-a', DISK],
                   input=f'm {R.SLOT0:x} {20 * R.STRIDE}\nq\n', capture_output=True, text=True, cwd=MAIN, env=env)
hexs = ''
for line in p.stdout.splitlines():   # `m a n` prints the n bytes as one line of hex pairs (repl.py's mem() reads it so)
    t = line.split()
    if t and all(len(x) == 2 and all(c in '0123456789abcdef' for c in x) for x in t):
        hexs += ''.join(t)
raw = bytes.fromhex(hexs)
print(f'REPL m dump: {len(raw)} bytes (expected {20 * R.STRIDE})')
if len(raw) != 20 * R.STRIDE:
    print(p.stdout[:2000]); sys.exit('m dump parse failed')
compare('REPL m dump (no step)', {n: raw[n * R.STRIDE:(n + 1) * R.STRIDE] for n in (6, 7, 16)})

# (2) repl.py's own Repl and slot() helper (it steps 1 instruction first)
r = R.Repl(SNAP)
try:
    live = {n: R.slot(r, n) for n in (6, 7, 16)}
finally:
    r.close()
compare('repl.py Repl.slot() (after s 1)', live)

# negative control: the same comparison with slot 7's bytes put against layout's slot 6 must report mismatches
print('negative control (slot 7 bytes vs layout slot 6):')
compare('control', {6: raw[7 * R.STRIDE:8 * R.STRIDE]})
