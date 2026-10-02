"""The lords of a built land and the buildings of each lord's chain, against the layout `$2eac`/`$2fc0` placed them from.

For every lord record of `$4e514` (stride 32, 64 records; byte 0 side, byte 1 kind, word 2 the head of the settlement chain as a
byte offset into `$4f916`, next at +8 of a building) that owns a chain it compares the multiset of building kinds on the chain with
the layout of the lord's kind (`$3078`, see `town_layouts.py`) and prints, per land, the lords by kind, how many chains equal their
layout exactly, how many sites a chain lost (a record over open sea or an occupied cell is refused), whether any building is not in
the layout, and the building kinds seen. A land has one captain per lord of kind 4 or 5 (`economy.md` 5a): `pop_census.py` counts
the captains the build gave out and this prints the lords they should match.

    cd M68000 && python reversing/powermonger/py/lord_chains.py scratchpad/pm139/corpus_2984/k*_1.ram      # preview roll
    python reversing/powermonger/py/lord_chains.py scratchpad/pm142/corpus_2984a/k*_1.ram                  # Play Random Land roll

Run on the entry state of `$2984`, so the chains are the finished map's and no man exists yet. Reads RAM only.
"""
import collections
import struct
import sys
from pathlib import Path

HOUSES, LORDS = 0x4f916, 0x4e514
NAMES = "TownHall Tavern FishHut FarmHouse Ranch Barn Church WorkShop Turret Square Ruin Tower Mine".split()
w = lambda r, a: struct.unpack_from(">H", r, a)[0]


def layout(r, kind):
    a = 0x3078 + w(r, 0x3078 + 2 * kind)
    out = []
    while r[a] != 0x9d and len(out) < 64:
        out.append(r[a + 2])
        a += 3
    return collections.Counter(out)


tot = collections.Counter()
seen = collections.Counter()
for path in sys.argv[1:]:
    r = Path(path).read_bytes()
    lords = collections.Counter()
    exact = lost = foreign = 0
    for i in range(64):
        b = LORDS + 32 * i
        kind, head = r[b + 1], w(r, b + 2)
        if not head:
            continue
        chain, off = collections.Counter(), head
        while off and sum(chain.values()) < 400:
            chain[r[HOUSES + off + 7]] += 1
            off = w(r, HOUSES + off + 8)
        lords[kind] += 1
        lay = layout(r, kind) if 1 <= kind <= 6 else None
        if lay is None:
            continue
        if chain == lay:
            exact += 1
        else:
            lost += sum((lay - chain).values())
            foreign += sum((chain - lay).values())
        seen.update(chain)
    n = sum(lords.values())
    tot.update(lords=n, exact=exact, lost=lost, foreign=foreign, capt=lords[4] + lords[5])
    print(f"{Path(path).stem:10} lords {n:3d} by kind {dict(sorted(lords.items()))} exact {exact} lost sites {lost} "
          f"not in layout {foreign} captains expected {lords[4] + lords[5]}")
print(f"total: lords {tot['lords']}, chain equals layout {tot['exact']}, sites lost {tot['lost']}, "
      f"buildings not in the layout {tot['foreign']}, lords of kind 4/5 {tot['capt']}")
print("kinds seen:", ", ".join(f"{NAMES[k]} {n}" for k, n in seen.most_common()))
