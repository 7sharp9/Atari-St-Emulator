"""bisect2.py <good.snap> <bad.snap>: both stopped at the first scatter call $236f8. Poke the power-up RNG seed into both (labelled poke),
run to $230c0, and compare the object map $32a58..$42a58. ddmin over the differing byte ranges of [$400,$70000) copied good->bad (pokes)."""
import sys, os; sys.path.insert(0, os.path.dirname(__file__))
import drv
good, bad = sys.argv[1], sys.argv[2]; lo, hi = 0x400, 0x70000
def dump(s):
    cmds = [f'm {x:x} {min(0x10000, hi-x):#x}' for x in range(lo, hi, 0x10000)]
    return b''.join(drv.mem(drv.run(s, cmds)))
G, B = dump(good), dump(bad)
rng = []
for i in range(len(G)):
    if G[i] != B[i] and not (0x2706e <= i+lo < 0x27076):
        if rng and i - rng[-1][1] <= 4: rng[-1][1] = i
        else: rng.append([i, i])
rng = [(s+lo, e+lo) for s, e in rng]
print(len(rng), 'ranges', sum(e-s+1 for s, e in rng), 'bytes (RNG excluded)', flush=True)
SEED = ['w 2706e 1234abdf', 'w 27072 5678e7f2']
def mapafter(snap, pokes):
    rows = drv.mem(drv.run(snap, pokes + SEED + ['bp 230c0 150000000'] + [f'm {x:x} 0x1000' for x in range(0x32a58, 0x42a58, 0x1000)]))
    return b''.join(rows[-16:])
ref = mapafter(good, [])
print('bad as is: map equals good\'s:', mapafter(bad, []) == ref, flush=True)
def pk(rs): return [f'wb {a:x} {G[a-lo]:02x}' for s, e in rs for a in range(s, e+1)]
ok = lambda rs: mapafter(bad, pk(rs)) == ref
print('all ranges poked:', ok(rng), flush=True)
def ddmin(rs):
    n = 2
    while len(rs) >= 2:
        chunk = max(1, len(rs)//n); subs = [rs[i:i+chunk] for i in range(0, len(rs), chunk)]; done = False
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
print('minimal:', len(mn), 'ranges', sum(e-s+1 for s, e in mn), 'bytes')
for s, e in mn: print(f'  ${s:06x}..${e:06x} good={G[s-lo:s-lo+8].hex()} bad={B[s-lo:s-lo+8].hex()}')
