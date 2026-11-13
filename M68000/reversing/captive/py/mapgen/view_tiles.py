"""Put the party in front of a cell holding a chosen tile and render the first-person view.

    uv run python -I reversing/captive/py/mapgen/view_tiles.py <snap> <outdir> <tile_hex>[@x,y] ... [--dist N] [--n K]

For each tile code, up to K cells of the live map (fed 9242(A6) = $1d9e8, y*64+x) holding it (bit 7 ignored), or the
named cell, are tried: the party is put by labelled pokes on an open cell (tile > $1a) N cells away (default 1) in a
straight line, facing the target (party x, y, facing = fed 26/28/30(A6); facing 0 N, 1 W, 2 S, 3 E, measured by
die_all.py), the game runs 180,000 steps (three main frames), the state is saved as <outdir>/t<tile>_<x>_<y>_d<N>.snap
and rendered with tools/snap_render.py to the same name .png (view area enlarged 3x as _view.png). Prints the cell-ahead
byte 15408(A6) so a render can be checked against the map.
"""
import os
import subprocess
import sys


def root():
    d = os.environ.get('M68000_ROOT') or os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(d, 'tools', 'rdis.py')):
        p = os.path.dirname(d)
        if p == d:
            sys.exit('repo root (tools/rdis.py) not found')
        d = p
    return d


R = root()
sys.path.insert(0, os.path.join(R, 'tools'))
from stclient import StServer  # noqa: E402
from PIL import Image  # noqa: E402

A6 = 0x1b5ce
POSX, POSY, FACE = A6 + 26, A6 + 28, A6 + 30
MAP = A6 + 9242
AHEAD = A6 + 15408
ALL = os.environ.get('VIEW_ALL_FACES') == '1'  # try every open approach, not only the first (names get _f<facing>)
STEP = {0: (0, -1), 1: (-1, 0), 2: (0, 1), 3: (1, 0)}


def main():
    args = sys.argv[1:]
    dist, nmax = 1, 2
    if '--dist' in args:
        i = args.index('--dist'); dist = int(args[i + 1]); del args[i:i + 2]
    if '--n' in args:
        i = args.index('--n'); nmax = int(args[i + 1]); del args[i:i + 2]
    snap, outdir, specs = args[0], os.path.abspath(args[1]), args[2:]
    os.makedirs(outdir, exist_ok=True)
    s = StServer(R)
    s('load', snapshot=snap)
    base = s('fork')['id']
    grid = s.read(MAP, 2048)
    tile = lambda x, y: grid[y * 64 + x] & 0x7f if 0 <= x < 64 and 0 <= y < 32 else 0
    for spec in specs:
        t, _, at = spec.partition('@')
        t = int(t, 16)
        cells = [tuple(map(int, at.split(',')))] if at else \
            [(i % 64, i // 64) for i in range(2048) if grid[i] & 0x7f == t]
        done = 0
        for (x, y) in cells:
            for face, (sx, sy) in STEP.items():
                px, py = x - sx * dist, y - sy * dist
                path = [(x - sx * k, y - sy * k) for k in range(1, dist + 1)]
                if not all(tile(*c) > 0x1a for c in path):
                    continue
                s('restore', id=base)
                s('poke', addr=POSX, width=2, value=px)
                s('poke', addr=POSY, width=2, value=py)
                s('poke', addr=FACE, width=2, value=face)
                s('step', n=180000)
                ahead = s.read(AHEAD, 1)[0]
                nx, ny, nf = (int.from_bytes(s.read(a, 2), 'big') for a in (POSX, POSY, FACE))
                name = os.path.join(outdir, f't{t:02x}_{x}_{y}_d{dist}' + (f'_f{face}' if ALL else ''))
                s('save', path=name + '.snap')
                subprocess.run(['uv', 'run', 'python', '-I', os.path.join(R, 'tools', 'snap_render.py'),
                                name + '.snap', name + '.png'], cwd=R, check=True, capture_output=True)
                im = Image.open(name + '.png').crop((28, 52, 182, 168))
                im.resize((im.width * 3, im.height * 3), Image.NEAREST).save(name + '_view.png')
                print(f'tile ${t:02x} cell ({x},{y}) from ({px},{py}) facing {face}; after run party ({nx},{ny}) f{nf}, '
                      f'15408(A6) ${ahead:02x} -> {name}_view.png')
                done += 1
                if not ALL:
                    break
            if done >= nmax:
                break
        if not done:
            print(f'tile ${t:02x}: no cell with an open approach at distance {dist}')
    s.close()


main()
