"""check_refusal.py [snaplist ...]  (PowerMonger 148th, agent A)

Is the `$6822` refusal (`$6884`) reachable?  It refuses an order of type T for a group in state S only when
`$6888[T] != 0 and $6888[T] == S` (and D7 != 0, or T != $0c).  The call sites and the states they are reached in are
read from the code (strategy.md "The commander AI"; listing in list_6522.txt):

  $65d2/$6676  type $08 via $67ee, from $65b4 / $664c   (group state 6 or 9)
  $6610/$6642  type $0c                                  (group state 6 or 9)
  $669a        type $04                                  (group state 6 or 9)
  $66b4        type $06                                  (group state 6 or 9)
  $67b4        type = the follow-up table entry          (group state 6 only: `$6762` is called only from $65aa)
  $674a        type $02 from $66e8                       (any state but 6 and 9 whose flag byte at $6750+state is nonzero)

This script reads `$6888`, `$6750`, `$67d0` from the snapshots, checks they are byte-identical in all of them (code segment
constants), and enumerates every (site, state, type) triple for a refusal.  Prints the count of refusing triples (expected 0).
"""
import os
import struct
import sys
from pathlib import Path


def _root():
    if os.environ.get('M68000_ROOT'):
        return Path(os.environ['M68000_ROOT'])
    for p in Path(__file__).resolve().parents:
        if (p / 'tools' / 'pm_fsm_ref.py').exists():
            return p
    raise SystemExit('M68000 root not found')


ROOT = _root()
sys.path.insert(0, str(ROOT / 'tools'))
from disassemble import ram_from_snap  # noqa: E402


def tables(ram):
    goal = {t: struct.unpack_from('>H', ram, 0x6888 + t)[0] for t in range(0, 0x20, 2)}
    flags = [ram[0x6750 + s] for s in range(0, 0x12)]
    camp = []
    a = 0x67d0
    while struct.unpack_from('>H', ram, a)[0] != 0:
        camp.append(struct.unpack_from('>HHH', ram, a))
        a += 6
    return goal, flags, camp, bytes(ram[0x6522:0x6900])


def main():
    snaps = []
    for a in sys.argv[1:]:
        snaps += [a] if a.endswith('.snap') else [l.strip() for l in open(a) if l.strip()]
    if not snaps:
        snaps = [str(ROOT / 'scratchpad/pm143/run/p0k0_s1.snap')]
    ref = None
    same = 0
    for s in snaps:
        t = tables(ram_from_snap(s))
        if ref is None:
            ref = t
        if t == ref:
            same += 1
        else:
            print('DIFFERS', s)
    print('snapshots with identical $6522..$68ff code and tables:', same, 'of', len(snaps))
    goal, flags, camp, _ = ref
    print('goal states by type:', {hex(k): v for k, v in goal.items() if v})
    print('$6750 flag bytes by state:', {s: f for s, f in enumerate(flags) if f})
    print('follow-up table:', camp)
    decide_states = (6, 9)
    triples = []
    for site, types in (('$65d2', [8]), ('$6676', [8]), ('$6610', [0xc]), ('$6642', [0xc]), ('$669a', [4]), ('$66b4', [6])):
        for st in decide_states:
            for t in types:
                triples.append((site, st, t))
    for ent in camp:
        triples.append(('$67b4', 6, ent[1]))
    for st in range(0, 0x12):
        if st in decide_states:
            continue                     # $6522 sends 6 and 9 to the decision, never to $66e8
        if flags[st] != 0:
            triples.append(('$674a', st, 2))
    refusing = []
    for site, st, t in triples:
        g = goal.get(t, 0)
        if g != 0 and g == st:
            refusing.append((site, st, t))
    print('reachable (site, state, type) triples:', len(triples))
    for tr in triples:
        print('  ', tr, 'goal', goal.get(tr[2], 0), 'REFUSES' if tr in refusing else '')
    print('refusing triples:', len(refusing))


if __name__ == '__main__':
    main()
