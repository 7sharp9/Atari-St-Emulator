"""plane_ab.py [<snap>]: poke-and-render A/B on the $438ee planes under the camera.

Runs: base (no poke), alt (-16514 plane = 0x3c, the 135th control), p-8257 (0x3c), p0 (0x3c), flag80 (+8257 plane = 0x80),
flag00 (+8257 = 0). Every run zeroes the $f890 camera cache, steps 1M, snapshots, renders; prints pixels differing from base.
Output under scratchpad/pm136/planes/ab/. Run from M68000/:  python3 reversing/powermonger/py/plane_ab.py [snap]
"""
import os, subprocess, sys
from pathlib import Path
from PIL import ImageChops, Image
ROOT = Path(__file__).resolve().parents[3]
snap = sys.argv[1] if len(sys.argv) > 1 else 'scratchpad/pm123/win/m1_s0.snap'
tag = Path(snap).stem
W = ROOT / 'scratchpad/pm136/planes/ab'
W.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(ROOT / 'tools'))
from pm_export import ram_from_snap
ram = ram_from_snap(ROOT / snap)
w = lambda a: int.from_bytes(ram[a:a + 2], 'big')
cell = 0x438ee + w(0x4bb3a) - w(0x57ffc) + ((w(0x4bb3c) - w(0x57ffc)) << 6)
runs = {'base': None, 'alt': (-16514, '3c'), 'm8257': (-8257, '3c'), 'p0': (0, '3c'),
        'flag80': (8257, '80'), 'flag00': (8257, '00')}
if len(sys.argv) > 2: runs = {k: v for k, v in runs.items() if k in ('base',) + tuple(sys.argv[2:])}
env = dict(os.environ, ATARI_NOTRACE='1')
png = {}
for name, p in runs.items():
    cmds = ['w f890 00000000']
    if p:
        off, b = p
        cmds += ['w %x %s' % ((cell + off + dr * 64 + dc) & ~1, b * 4) for dr in range(-6, 7) for dc in (-4, 0, 4)]
    out = W / ('%s_%s.snap' % (tag, name))
    cmds += ['s 1000000', 'snap %s' % out, 'q']
    (W / ('%s_%s.cmds' % (tag, name))).write_text('\n'.join(cmds) + '\n')
    subprocess.run(['dotnet', 'exec', 'bin/Debug/net8.0/M68000.dll', 'resume', snap, 'repl', '--disk-a', 'scratchpad/powermonger.st'],
                   stdin=(W / ('%s_%s.cmds' % (tag, name))).open(), capture_output=True, cwd=ROOT, env=env)
    png[name] = W / ('%s_%s.png' % (tag, name))
    subprocess.run([sys.executable, 'tools/snap_render.py', str(out), str(png[name])], capture_output=True, cwd=ROOT)
b = Image.open(png['base']).convert('RGB')
print('cell $%x (plane base)' % cell)
for name in runs:
    if name == 'base': continue
    d = ImageChops.difference(b, Image.open(png[name]).convert('RGB'))
    n = sum(1 for q in d.get_flattened_data() if q != (0, 0, 0))
    print('%-8s %6d pixels differ, bbox %s' % (name, n, d.getbbox()))
