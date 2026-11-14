"""deaths.py <snap> <loops> [chunk]: fly a demo with a breakpoint on the life decrement $25ba0, in chunks of <chunk> steps (default 100M).
After every chunk print PC, lives $32a54, wave $32a50, tick $32a44, score $2708e (signed long), fuel $32a2e.  PC = 00025ba0 marks a life
loss (values read before the decrement).  Nothing is poked."""
import sys, os; sys.path.insert(0, os.path.dirname(__file__))
import drv
snap, loops = sys.argv[1], int(sys.argv[2]); chunk = sys.argv[3] if len(sys.argv) > 3 else '100000000'
cmds = []
for i in range(loops): cmds += [f'bp 25ba0 {chunk}', 'r', 'm 32a54 2', 'm 32a50 2', 'm 32a44 2', 'm 2708e 4', 'm 32a2e 2']
lines = drv.run(snap, cmds)
pcs = [l.split()[1] for l in lines if l.startswith('PC:')]
rows = drv.mem(lines)
# every chunk prints PC twice (the stop message and r) and five memory rows
pcs = pcs[0::2] if len(pcs) == 2*loops else pcs
tot = 0
for i in range(loops):
    r = rows[5*i:5*i+5]
    if len(r) < 5: print('chunk', i+1, 'missing'); break
    v = [int.from_bytes(x, 'big', signed=(k == 3)) for k, x in enumerate(r)]
    print(f"chunk {i+1}: pc={pcs[i]} life_loss={'yes' if pcs[i].endswith('25ba0') else 'no'} lives={v[0]} wave={v[1]} tick={v[2]} score={v[3]} fuel={v[4]}")
