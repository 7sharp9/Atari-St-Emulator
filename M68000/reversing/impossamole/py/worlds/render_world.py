"""Render every per-world Impossamole asset from one gameplay snapshot with the existing py/ tools.

    uv run python <this dir>/render_world.py <snap> <prefix> <outdir> [--cat-blocks B1]

Writes <outdir>/<prefix>_{tileset,level_tiles,categories_start,categories_all,level_map,level_map_raw,
sprites_bank1,sprites_bank2,spawn_types}.png and prints the tiles.py --check match rate.

Why a wrapper: level_map.CATCOL / tiles.CATTINT know only categories 0,1,2,3,4,9 (the Amazon set); Ice Land's
$25000 table also uses 7 and Bermuda Triangle's 5, 6, 7, 8; level_map.py raises KeyError on them. This script adds
colours for 5-8 before calling the unchanged tools.
"""
import os, subprocess, sys
from pathlib import Path

ROOT = Path(os.environ.get('M68000_ROOT', os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..'))))
PY = ROOT / 'reversing' / 'impossamole' / 'py'
sys.path.insert(0, str(PY))
sys.path.insert(0, str(ROOT / 'tools'))
import level_map, tiles  # noqa: E402

# 5 = conveyor left, 6 = conveyor right ($00c362-$00c446), 7 = ice ($00c536-$00c5ba), 8 = slow wade ($00c92a-$00c994)
level_map.CATCOL.update({5: (255, 160, 60), 6: (255, 220, 120), 7: (120, 230, 240), 8: (40, 200, 200)})
tiles.CATTINT.update({5: (255, 150, 0), 6: (255, 230, 0), 7: (0, 230, 255), 8: (0, 120, 255)})


def run_main(mod, argv):
    old = sys.argv
    sys.argv = [mod.__name__] + argv
    try:
        mod.main()
    finally:
        sys.argv = old


def main():
    snap, prefix, out = sys.argv[1], sys.argv[2], Path(sys.argv[3])
    out.mkdir(parents=True, exist_ok=True)
    nb = int(sys.argv[sys.argv.index('--cat-blocks') + 1]) if '--cat-blocks' in sys.argv else 420
    f = lambda n: str(out / f'{prefix}_{n}.png')
    run_main(tiles, [snap, '--sheet', f('tileset'), '--scale', '3'])
    run_main(tiles, [snap, '--level', f('level_tiles'), '--scale', '1'])
    run_main(tiles, [snap, '--cats', f('categories_start'), '--b0', '0', '--b1', '80'])
    run_main(tiles, [snap, '--cats', f('categories_all'), '--b0', '0', '--b1', str(nb)])
    run_main(level_map, [snap, f('level_map'), '--rooms'])
    run_main(level_map, [snap, f('level_map_raw'), '--rooms', '--raw'])
    run_main(tiles, [snap, '--check'])
    for b in (1, 2):
        subprocess.run([sys.executable, str(PY / 'sprites.py'), snap, '--bank', str(b), f(f'sprites_bank{b}')], check=True)
    subprocess.run([sys.executable, str(PY / 'spawn_types.py'), snap, '--sheet', f('spawn_types')], check=True,
                   stdout=open(out / f'{prefix}_spawn_types.txt', 'w'))


if __name__ == '__main__':
    main()
