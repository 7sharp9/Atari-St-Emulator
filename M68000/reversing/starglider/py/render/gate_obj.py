"""Gate for the whole object draw $f6a8 (model lookup, matrix, face culling, vertex cache, edge draw) against rref.f6a8 on natural states.

    python3 gate_obj.py <start snap> <ncaptures> [--control]     # default snapshot g_game2
For `ncaptures` natural entries of $f6a8 (every k-th hit from the start snapshot; k from the hit census) the REPL snapshots the state, runs
`callcap f6a8` and the reference is run from that snapshot's RAM with the entry D0 (model type) and D5.  Compared: the complete memory delta
(globals, flag arrays, vertex cache, screen bytes) outside the stack.  --control: the culling test uses `dot > 0` instead of `dot < 0`.
Expected output: `f6a8 n/n` and the per-type tally."""
import os, sys, json, collections
here = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, here)
import rcommon as R
import rref as F
snap = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith('--') else R.SNAP_GAME2
n = int(sys.argv[2]) if len(sys.argv) > 2 and not sys.argv[2].startswith('--') else 12
if '--control' in sys.argv:
    src = open(os.path.join(here, 'rref.py')).read().replace("draw = dot < 0", "draw = dot > 0")
    import types; F2 = types.ModuleType('rref_bad'); exec(compile(src, 'rref_bad', 'exec'), F2.__dict__); F = F2
OUT = R.WORK + '/render/caps/obj'
hits = list(range(1, 2 + 8 * n, 8))[:n]
txt = R.cap_calls(snap, 0xf6a8, hits, OUT, 'o', callcap_steps=600000)
ok = 0; tally = collections.Counter()
for h in hits:
    j = json.load(open(f'{OUT}/o_{h}.json'))
    ram = R.load_ram(f'{OUT}/o_{h}.snap')
    m = F.Mem(ram)
    D0 = j['reg0'][0] & 0xFFFF; D5 = j['reg0'][5]
    F.f6a8(m, D0, D5)
    stack = (j['entrySP'] - 512, j['entrySP'] + 16)
    got = {a: nw for a, o, nw in j['mem'] if not (stack[0] <= a < stack[1])}
    want = m.changes()
    good = got == want
    ok += good
    tally[(D0, good)] += 1
    if not good:
        d = sorted(set(got) ^ set(want) | {a for a in got if a in want and got[a] != want[a]})
        print('MISS hit', h, 'type', D0, 'diff addrs', [hex(a) for a in d[:12]], len(d))
print(f'f6a8 {ok}/{len(hits)}   (type, ok): {sorted(tally.items())}')
os.system(f'rm -f {OUT}/o_*.snap')
