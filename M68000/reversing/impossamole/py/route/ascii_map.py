"""ASCII collision map of an Impossamole room from a snapshot.

    uv run python ascii_map.py <snap> <col0> <col1> [rows]

One char per 8px tile, by $25000 category: '.' 0, '#' 4 walkable, 'X' 9 hazard, 'L' 1 (ladder), '=' 2 (ledge), 'o' 3.
Prints a ruler of block numbers (col//4) so exits can be read off.
"""
import os, sys
ROOT = os.environ.get('M68000_ROOT', os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..')))
sys.path.insert(0, os.path.join(ROOT, 'reversing/impossamole/py'))
from level_map import load

CH = {0: '.', 4: '#', 9: 'X', 1: 'L', 2: '=', 3: 'o'}


def dump(snap, c0, c1):
    ram, tiles, cls = load(snap)
    print('col/10 ' + ''.join(str((c // 10) % 10) if c % 10 == 0 else ' ' for c in range(c0, c1)))
    print('col%10 ' + ''.join(str(c % 10) for c in range(c0, c1)))
    print('blk    ' + ''.join(str((c // 4) % 10) if c % 4 == 0 else ' ' for c in range(c0, c1)))
    for r in range(24):
        print(f'y{r*8:3d}  ' + ''.join(CH[cls[tiles[r][c]]] for c in range(c0, c1)))


if __name__ == '__main__':
    dump(sys.argv[1], int(sys.argv[2]), int(sys.argv[3]))
