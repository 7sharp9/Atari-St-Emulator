import sys; sys.path.insert(0, __import__('os').path.dirname(__file__))
import drv
snap, n, step = sys.argv[1], int(sys.argv[2]), sys.argv[3]
cmds = []
for i in range(n):
    cmds += ['s '+step, 'm 32a44 2', 'm 270b0 12', 'm 62a5f 1', 'm 62a5b 1', 'm 2709a 4', 'm 32a52 2', 'm 2708e 4']
rows = drv.mem(drv.run(snap, cmds))
assert len(rows) == 7*n, len(rows)
for i in range(n):
    t, sh, d, k, hs, lf, sc = rows[7*i:7*i+7]
    w = lambda b, o: int.from_bytes(b[o:o+2], 'big', signed=True)
    print(f"{i:3d} tick={int.from_bytes(t,'big'):5d} ship=({int.from_bytes(sh[0:2],'big'):5d},{int.from_bytes(sh[2:4],'big'):5d},{int.from_bytes(sh[4:6],'big'):5d}) v=({w(sh,6)},{w(sh,8)},{w(sh,10)}) demo={d[0]:02x} key={k[0]:02x} hi={int.from_bytes(hs,'big')} w32a52={int.from_bytes(lf,'big')} score={int.from_bytes(sc,'big')}")
