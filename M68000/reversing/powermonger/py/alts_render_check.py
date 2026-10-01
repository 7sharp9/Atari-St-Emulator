"""alts_render_check.py [<snap>]: $3f86c is the terrain height plane the renderer projects (not a control/influence byte).

The terrain redraw `$f898` -> `$fec6` runs only when the camera word cache `$f890/$f892`, the rotation `$ff9a` or the zoom
`$fdec` changed, so the script zeroes the cache (`w f890 00000000`) in both runs to force one redraw, and in the second run
also writes 0x3c into a block of `$3f86c` cells under the camera (13 rows x 3 longwords around
`$3f86c + $4bb3a - $57ffc + (($4bb3c - $57ffc) << 6)`, the A1 `$fee8..$ff08` computes for the projector). Each run
steps 1M, snapshots and renders; the diff is the pixels the poke changed: a raised plateau, 10938 pixels inside the map
window (96,21)-(286,155) on pm123/win/m1_s0.snap, 0 for the same run without a poke or with no cache clear.

    cd M68000 && python3 reversing/powermonger/py/alts_render_check.py [scratchpad/pm123/win/m1_s0.snap]

Needs bin/Debug/net8.0/M68000.dll, scratchpad/powermonger.st, Pillow (uv env). Output under ${PM_WORK:-scratchpad/pmwork}/alts/;
open alt_poke.png beside alt_base.png to see the plateau.
"""
import os
import subprocess
import sys
from pathlib import Path

from PIL import ImageChops, Image

ROOT = Path(__file__).resolve().parents[3]
snap = sys.argv[1] if len(sys.argv) > 1 else 'scratchpad/pm123/win/m1_s0.snap'
W = ROOT / os.environ.get('PM_WORK', 'scratchpad/pmwork') / 'alts'
W.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(ROOT / 'tools'))
from pm_export import ram_from_snap  # noqa: E402

ram = ram_from_snap(ROOT / snap)
w = lambda a: int.from_bytes(ram[a:a + 2], 'big')
cell = 0x3f86c + w(0x4bb3a) - w(0x57ffc) + ((w(0x4bb3c) - w(0x57ffc)) << 6)
env = dict(os.environ, ATARI_NOTRACE='1')
png = {}
for name, poke in (('base', False), ('poke', True)):
    cmds = ['w f890 00000000']
    if poke:
        cmds += ['w %x 3c3c3c3c' % (cell + dr * 64 + dc) for dr in range(-6, 7) for dc in (-4, 0, 4)]
    out = W / ('alt_%s.snap' % name)
    cmds += ['s 1000000', 'snap %s' % out, 'q']
    (W / ('alt_%s.cmds' % name)).write_text('\n'.join(cmds) + '\n')
    subprocess.run(['dotnet', 'exec', 'bin/Debug/net8.0/M68000.dll', 'resume', snap, 'repl', '--disk-a', 'scratchpad/powermonger.st'],
                   stdin=(W / ('alt_%s.cmds' % name)).open(), capture_output=True, cwd=ROOT, env=env)
    png[name] = W / ('alt_%s.png' % name)
    subprocess.run([sys.executable, 'tools/snap_render.py', str(out), str(png[name])], capture_output=True, cwd=ROOT)
d = ImageChops.difference(Image.open(png['base']).convert('RGB'), Image.open(png['poke']).convert('RGB'))
n = sum(1 for p in d.get_flattened_data() if p != (0, 0, 0)) if hasattr(d, 'get_flattened_data') else sum(1 for p in d.getdata() if p != (0, 0, 0))
print('poked cell block at $%x: %d pixels differ, bbox %s' % (cell, n, d.getbbox()))
