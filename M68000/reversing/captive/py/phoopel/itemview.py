"""Control render: a clipboard on an ordinary floor cell, seen from 1 cell away and from its own cell (labelled
pokes of party x, y, facing), to compare with the clipboard inside the flame cell (7,9)."""
import os, sys, subprocess
import os as _os
_M = _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '../../../..'))  # M68000/
sys.path.insert(0, _M + '/reversing/captive/py/ai')
from cap import R, StServer, A6  # noqa: E402
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__))
s = StServer(R); s('load', snapshot=os.path.join(HERE, 'base13.snap')); base = s('fork')['id']
g = s.read(A6 + 9242, 2048)
print('tiles around (25,2):', {c: hex(g[c[1]*64+c[0]]) for c in [(24,2),(26,2),(25,1),(25,3),(25,2)]})
for name, (px, py, f) in [(a, b) for a, b in [(n, v) for n, v in (('clip_from_W', (24, 2, 3)), ('clip_from_E', (26, 2, 1)), ('clip_from_S', (25, 3, 0)), ('clip_own_cell_E', (25, 2, 3)))]]:
    x, y = px, py
    if g[y*64+x] & 0x7f <= 0x1a:
        continue
    s('restore', id=base)
    for a, v in ((26, px), (28, py), (30, f)):
        s('poke', addr=A6 + a, width=2, value=v)
    s('step', n=180000)
    p = os.path.join(HERE, name + '.snap'); s('save', path=p)
    subprocess.run(['uv', 'run', 'python', '-I', os.path.join(R, 'tools', 'snap_render.py'), p, p[:-5] + '.png'], cwd=R, check=True, capture_output=True)
    im = Image.open(p[:-5] + '.png').crop((28, 52, 182, 168)); im.resize((im.width*3, im.height*3), Image.NEAREST).save(p[:-5] + '_view.png')
    print(name, 'ahead', hex(s.read(A6 + 15408, 1)[0]))
s.close()
