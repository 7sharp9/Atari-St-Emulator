"""bisect.py <good.snap> <bad.snap> <lo> <hi> <nsamp>: both snapshots stop at the same PC. Find a minimal set of differing
byte RANGES which, poked (labelled pokes) from good into bad, make bad's trajectory (nsamp samples of 200k steps) equal good's.
Delta debugging (ddmin) over merged diff ranges."""
import sys, os; sys.path.insert(0, os.path.dirname(__file__))
import drv
good, bad, lo, hi, ns = sys.argv[1], sys.argv[2], int(sys.argv[3], 16), int(sys.argv[4], 16), int(sys.argv[5])
def dump(s):
    cmds = [f'm {x:x} {min(0x10000, hi-x):#x}' for x in range(lo, hi, 0x10000)]
    return b''.join(drv.mem(drv.run(s, cmds)))
G, B = dump(good), dump(bad)
rng = []
for i in range(len(G)):
    if G[i] != B[i]:
        if rng and i - rng[-1][1] <= int(os.environ.get("BGAP", "8")): rng[-1][1] = i
        else: rng.append([i, i])
rng = [(s+lo, e+lo) for s, e in rng]
print(len(rng), 'ranges', sum(e-s+1 for s, e in rng), 'bytes', flush=True)
def traj(snap, pokes):
    cmds = list(pokes)
    for i in range(ns): cmds += ['s 200000', 'm 32a44 2', 'm 270b0 12']
    rows = drv.mem(drv.run(snap, cmds)); return [r.hex() for r in rows]
ref = traj(good, [])
def pokes_for(rs):
    out = []
    for s, e in rs:
        for a in range(s, e+1): out.append(f'wb {a:x} {G[a-lo]:02x}')
    return out
def ok(rs): return traj(bad, pokes_for(rs)) == ref
print('bad as is matches good:', traj(bad, []) == ref)
print('all ranges poked matches good:', ok(rng), flush=True)
def ddmin(rs):
    n = 2
    while len(rs) >= 2:
        chunk = max(1, len(rs)//n); subs = [rs[i:i+chunk] for i in range(0, len(rs), chunk)]
        done = False
        for s in subs:
            if ok(s): rs, n, done = s, 2, True; break
        if not done:
            for i in range(len(subs)):
                comp = [r for j, s in enumerate(subs) if j != i for r in s]
                if comp and ok(comp): rs, n, done = comp, max(n-1, 2), True; break
        if not done:
            if n >= len(rs): break
            n = min(len(rs), n*2)
    return rs
mn = ddmin(rng)
print('minimal ranges:', len(mn), 'bytes', sum(e-s+1 for s, e in mn))
for s, e in mn: print(f'  ${s:06x}..${e:06x} good={G[s-lo:s-lo+8].hex()} bad={B[s-lo:s-lo+8].hex()}')
