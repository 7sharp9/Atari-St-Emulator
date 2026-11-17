"""Gate for the new-person generator `$17c46` (README, "A new person"): calls the game's routine in `stserver` with
the TOS Random seed (`$29b8`) poked to each of N values and checks every drawn trait, the derived wake hour and the
name copied from the NAMES file against `lcp_model.new_person`.

usage: gate_newperson.py [n_seeds] [seed]
Needs $LCP_WORK (default <root>/scratchpad/lcp) holding house.snap, disk/tmbird03_even.st and files/LCP/DATA/NAMES.
Labelled poke: the seed long at $29b8 (0 is skipped: TOS reseeds from the 200 Hz clock then).
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

N = int(sys.argv[1]) if len(sys.argv) > 1 else 100
rng = random.Random(int(sys.argv[2]) if len(sys.argv) > 2 else 1)
names = open(os.path.join(WORK, 'files', 'LCP', 'DATA', 'NAMES'), 'rb').read()
s = StServer(root)
s('load', snapshot=os.path.join(WORK, 'house.snap'), disk=os.path.join(WORK, 'disk', 'tmbird03_even.st'))
base = s('fork')['id']
VARIANTS = ['true', 'swap_unused_personality', 'sleep_22_23']
score = {v: 0 for v in VARIANTS}
pers = [0] * 8
for i in range(N):
    s('restore', id=base)
    seed = rng.randrange(1, 1 << 32)
    s('poke', addr=m.SEED, width=4, value=seed)
    s.call(0x17c46, max_steps=2000000)
    got = {f: int.from_bytes(s.read(a, 2), 'big') for f, a, _, _ in m.NEW_DRAWS if a}
    got['wake'] = int.from_bytes(s.read(0x5142c, 2), 'big')
    got['name'] = s.read(0x5149c, 10)
    pers[got['personality']] += 1
    for v in VARIANTS:
        exp = m.new_person(seed, names, v)
        if all(exp[k] == got[k] for k in got):
            score[v] += 1
        elif v == 'true':
            print('MISMATCH', hex(seed), {k: (exp[k], got[k]) for k in got if exp[k] != got[k]})
s.close()
print(f'seeds {N}; personalities drawn: {pers}')
for v in VARIANTS:
    tag = '' if v == 'true' else ('  control FAILS (good)' if score[v] < score['true'] else '  control PASSES (corpus too weak)')
    print(f'{v:24s} {score[v]}/{N}{tag}')
