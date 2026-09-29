import sys, os
ROOT = os.environ.get('M68000_ROOT', os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..')))
sys.path.insert(0, os.path.join(ROOT, 'reversing/impossamole/py'))
import level_map
snap, b0, b1 = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
ram, tiles, cls = level_map.load(snap)
ch = {0: '.', 4: '#', 9: 'X', 1: 'H', 2: '-', 3: '/'}
print('     ' + ''.join(str((b * 4 // 4) % 10) if c == 0 else ' ' for b in range(b0, b1) for c in range(4)))
for r in range(24):
    print('%3d  ' % (r * 8) + ''.join(ch[cls[tiles[r][c]]] for c in range(b0 * 4, b1 * 4)))
