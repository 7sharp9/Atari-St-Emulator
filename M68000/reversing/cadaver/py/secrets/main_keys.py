"""main_keys.py: the main loop's own keyboard handler ($006ba2-$006d10), which reads the IKBD current-key cell 2530(A5)=$018b34
and is separate from the $01616c KeyDispatchTable path the README's 9th pass exhausted.  For each scancode: fresh Repl from
gameplay_empire.snap, key held 60,000 steps (2+ main-loop iterations of ~25,000 steps), released, 300,000 more steps; prints hit
counts on each handler branch and the flag bytes before/after.
    uv run python reversing/cadaver/py/secrets/main_keys.py [scancode_hex ...]     (default: the list below)"""
import sys
sys.path.insert(0, __file__.rsplit('/', 1)[0])
from repl import *
BR = {0x6ba2: 'loop key read', 0x6bac: 'F2 toggle b0', 0x6bb8: 'F3 toggle b1', 0x6bc4: 'F4 toggle b2', 0x6bd0: 'S -> 2519 b3',
      0x6bde: 'L -> 2519 b4', 0x6bf2: 'C ($2e)', 0x6c04: 'P ($19)', 0x6c46: 'H ($23) enter', 0x6c7e: 'H second press', 0x6cb0: 'Down($50) b0',
      0x6cce: 'Ret/Space action21', 0x6d02: 'F1 ($3b)', 0x6d10: 'fallthrough'}
KEYS = {'F1': 0x3b, 'F2': 0x3c, 'F3': 0x3d, 'F4': 0x3e, 'S': 0x1f, 'L': 0x26, 'C': 0x2e, 'P': 0x19, 'H': 0x23, 'Return': 0x1c,
        'Space': 0x39, 'Down': 0x50, 'KpEnter': 0x72, 'Esc': 0x01}
FLAGS = {'2499': 2499, '2519': 2519, '2474': 2474, '2466': 2466, '2126': 2126, '1262': 1262, '2202': 2202}
def flags(r): return {k: r.a5(o, 2 if k in ('2126', '1262') else 1).hex() for k, o in FLAGS.items()}
def run(name, sc):
    r = Repl(); before = flags(r); tot = {}
    r.cmd(f'kbd {sc:02x}')
    for n in (60000,):
        for a, c in r.hits(n, *BR).items(): tot[a] = tot.get(a, 0) + c
    r.cmd(f'kbd {sc | 0x80:02x}')
    for a, c in r.hits(300000, *BR).items(): tot[a] = tot.get(a, 0) + c
    after = flags(r)
    print(f'{name} (${sc:02x}):', {BR[a]: c for a, c in tot.items() if c and a != 0x6ba2 and a != 0x6d10}, 'loop iters', tot.get(0x6ba2), 'fall', tot.get(0x6d10))
    print('   flags changed:', {k: (before[k], after[k]) for k in before if before[k] != after[k]} or 'none')
    r.close()
if __name__ == '__main__':
    sel = [int(x, 16) for x in sys.argv[1:]]
    for n, sc in KEYS.items():
        if not sel or sc in sel: run(n, sc)
