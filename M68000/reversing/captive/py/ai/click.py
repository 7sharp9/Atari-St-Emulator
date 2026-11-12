"""Click at a screen point: click.py <snap> <out.snap> <x> <y>. Pins the pointer top-left, moves, clicks."""
import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); from cap import *
s = srv(sys.argv[1]); x, y = int(sys.argv[3]), int(sys.argv[4])
for _ in range(3):
    s('mouse', action='move', dx=-127, dy=-127); s('step', n=30000)
while x or y:
    dx, dy = min(x, 120), min(y, 120); s('mouse', action='move', dx=dx, dy=dy); s('step', n=30000); x -= dx; y -= dy
before = s.read(A6 + 9242, 2048)
s('mouse', action='down', button='l'); s('step', n=60000); s('mouse', action='up', button='l'); s('step', n=600000)
after = s.read(A6 + 9242, 2048)
print('grid changes', [(i % 64, i // 64, hex(before[i]), hex(after[i])) for i in range(2048) if before[i] != after[i]])
print('pos', w16(s, 26), w16(s, 28), 'face', w16(s, 30))
s('save', path=os.path.abspath(sys.argv[2])); s('render', path=os.path.abspath(sys.argv[2]).replace('.snap', '.png')); s.close()
