"""Census of the group word at group view +204 (side view 280(), `strategy.md` "campaign phase / sub-order")
and +216 (side view 292()) across snapshots, by group state.

Group views are found from the live leads: every entity record (first 512 at $51b66, 50 bytes) with flag
byte 7 bit 4 and a nonzero word 42 names its group view at $51538 + word 42.

Writers of +204 in the text segment (whole-image listing, `pm_all.asm`): $4a7a (2, 6, 8, $c),
$4d68/$4d76 (D7 = the opponent's party class from $4de2), $57d8/$57e6 ($5778: 4, then the attacker's
entity offset over it).

Usage: python3 phase_census.py <snap-or-ram>...   (prints one line per group, then totals)
"""
import collections
import struct
import sys
from pathlib import Path


def root():
    p = Path(__file__).resolve()
    for d in p.parents:
        if (d / "tools" / "rdis.py").exists():
            return d
    sys.exit("repo root not found")


sys.path.insert(0, str(root() / "tools"))
from gfxview import load_ram  # noqa: E402

ENT, STRIDE, GRP = 0x51b66, 50, 0x51538
w = lambda m, a: struct.unpack_from(">h", m, a)[0]

tot = collections.Counter()
for path in sys.argv[1:]:
    ram, _ = load_ram(path, raw=path.endswith(".ram"))
    seen = set()
    for i in range(512):
        e = ENT + i * STRIDE
        if not (ram[e + 7] & 0x10):
            continue
        g = w(ram, e + 42)
        # a group view is 76 + 316*side + 2k (k 0..5); other word-42 values of flag-bit-4 records are not groups
        if g in seen or g < 76 or (g - 76) % 316 > 10 or (g - 76) % 2:
            continue
        seen.add(g)
        gv = GRP + g
        st, ph, opp = w(ram, gv), w(ram, gv + 204), w(ram, gv + 216)
        cls = ph if ph in (0, 2, 4, 6, 8, 10, 12) else "offset"
        tot[(st, cls)] += 1
        print(f"{Path(path).name:28s} grp {g:5d} state {st:3d} +204 {ph:6d} (${ph & 0xffff:04x}) +216 {opp:6d}")
print("\n(state, +204 class): count")
for k, v in sorted(tot.items(), key=lambda kv: (kv[0][0], str(kv[0][1]))):
    print(k, v)
