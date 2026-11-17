"""Gate for the secondary-desire chooser `$1747e` (README, "The behaviour scheduler"): runs the game's own routine
in `stserver` on poked states and checks the action it returns against `lcp_model.secondary`, which reproduces
TOS 1.00's XBIOS `Random` (seed at `$29b8`) so the prediction is exact, not a set membership.

usage: gate_secondary.py [n_states] [seed]
Needs $LCP_WORK (default <root>/scratchpad/lcp) holding house.snap and disk/tmbird03_even.st (scratchpad/ANCHORS.md).
Labelled pokes per state: current hour `$4ca20`, day of month `$4ca22`, wake hour `$5142c`, personality `$51434`,
illness `$5145a`, in-bed `$51460`, last action `$4c5a4`. The weekday is read from the game's own `$2459c` called
on the same poked state, and is an input to the model, not something this gate checks.
Each broken model (one rule changed) must score below the true model; the script prints every count.
"""
import os, random, sys

HERE = os.path.dirname(os.path.abspath(__file__))
root = os.environ.get('M68000_ROOT') or HERE
while not os.path.exists(os.path.join(root, 'tools', 'rdis.py')):
    root = os.path.dirname(root)
WORK = os.environ.get('LCP_WORK') or os.path.join(root, 'scratchpad', 'lcp')
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(root, 'tools'))
import lcp_model as m  # noqa: E402
from stclient import StServer  # noqa: E402

N = int(sys.argv[1]) if len(sys.argv) > 1 else 400
rng = random.Random(int(sys.argv[2]) if len(sys.argv) > 2 else 1)

s = StServer(root)
s('load', snapshot=os.path.join(WORK, 'house.snap'), disk=os.path.join(WORK, 'disk', 'tmbird03_even.st'))
base = s('fork')['id']
lists = m.read_tables(lambda a, n: s.read(a, n))
actions = sorted(set(lists['A'] + lists['B'] + lists['C']))

VARIANTS = ['true'] + m.BROKEN
score = {v: 0 for v in VARIANTS}
results = {}
for i in range(N):
    s('restore', id=base)
    st = dict(hour=rng.randrange(24), mday=rng.randrange(1, 29), wake=rng.randrange(24),
              personality=rng.randrange(8), ill=rng.choice([0, 0, 0, 1, 2, 3]), in_bed=rng.choice([0, 0, 0, 1]),
              last=rng.choice(actions + [-1]))
    for k, (addr, _) in m.FIELDS.items():
        s('poke', addr=addr, width=2, value=st[k] & 0xffff)
    s.call(0x2459c)
    st['weekday'] = s.reg('d0') & 0xffff
    s('restore', id=base)
    for k, (addr, _) in m.FIELDS.items():
        s('poke', addr=addr, width=2, value=st[k] & 0xffff)
    st['seed'] = int.from_bytes(s.read(m.SEED, 4), 'big')
    s.call(0x1747e)
    got = s.reg('d0') & 0xffff
    got = got - 0x10000 if got & 0x8000 else got
    for v in VARIANTS:
        if m.secondary(st, lists, v)[0] == got:
            score[v] += 1
    results[i] = (st, got)
s.close()

lists_used = {}
for st, got in results.values():
    lists_used[m.secondary(st, lists, 'true')[1]] = lists_used.get(m.secondary(st, lists, 'true')[1], 0) + 1
print(f'states {N}; list chosen by the true model: {dict(sorted(lists_used.items()))}')
for v in VARIANTS:
    tag = '' if v == 'true' else ('  control FAILS (good)' if score[v] < score['true'] else '  control PASSES (corpus too weak)')
    print(f'{v:14s} {score[v]}/{N}{tag}')
