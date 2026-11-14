"""traj.py <snap> <n> <step> [pokes...]: resume a snapshot, apply REPL poke lines, sample ship/tick/demo flag every <step> steps.
Prints one line per sample: tick x y z vx vy vz demo flag. Output is the trajectory used for run-vs-run comparison."""
import sys, os; sys.path.insert(0, os.path.dirname(__file__))
import drv
snap, n, step = sys.argv[1], int(sys.argv[2]), sys.argv[3]
pre = sys.argv[4:]
cmds = list(pre)
for i in range(n):
    cmds += ['s '+step, 'm 32a44 2', 'm 270b0 12', 'm 62a5f 1']
rows = drv.mem(drv.run(snap, cmds))
assert len(rows) == 3*n, len(rows)
w = lambda b, o: int.from_bytes(b[o:o+2], 'big')
for i in range(n):
    t, s, d = rows[3*i:3*i+3]
    print(w(t,0), *[w(s,o) for o in range(0,12,2)], d[0])
