"""Populous II object heap and per-cell occupant lists, checked on a snapshot.

Each cell record of the landscape ($3979e, 4 bytes per cell) keeps the head of a doubly linked
occupant list in its word 2: a signed offset from $3ff1a, 0 for none. The nodes are records of
four arrays that share a header (+0 type, +2 next, +4 prev, +6/+8 position words whose high
bytes are the cell x/y, +12 side, 0 = free): scenery $3f42a (200 x 14 bytes), entities $3ff1a
(400 x $34, record 0 the null sentinel), $4505a (250 x 32) and $46f9a (3 x 14). `$2436e` moves
an entity and relinks it (README "Objects and entities").

Checks:
  1. every cell list is well formed: each node is a record of one of the arrays, its prev is the
     previous node (0 at the head), and its own cell is the list's cell;
  2. every record whose side byte +12 is non-zero is in exactly one cell list (its own cell);
  3. control: the same check with the cell taken from bytes 7/9 (the low bytes) fails.

usage: uv run python reversing/populous2/py/walkers.py <snap> [--dump]
"""
import os
import sys


def m68000_root():
    d = os.path.dirname(os.path.abspath(__file__))
    while d != os.path.dirname(d):
        if os.path.exists(os.path.join(d, "tools", "rdis.py")):
            return d
        d = os.path.dirname(d)
    return os.environ["M68000_ROOT"]


sys.path.insert(0, os.path.join(m68000_root(), "tools"))
from gfxview import load_ram  # noqa: E402

CELLS = 0x3979E
ENT = 0x3FF1A
ESZ = 0x34
NENT = 400
ARRAYS = [("scenery", 0x3F42A, 14, 200), ("entity", ENT, ESZ, NENT),
          ("a4505a", 0x4505A, 32, 250), ("a46f9a", 0x46F9A, 14, 3)]


def record_of(addr):
    for name, base, size, n in ARRAYS:
        if base <= addr < base + size * n and (addr - base) % size == 0:
            return name
    return None


def w(ram, a):
    return (ram[a] << 8) | ram[a + 1]


def l(ram, a):
    return (w(ram, a) << 16) | w(ram, a + 2)


def check(ram, xo=6, yo=8):
    bad = []
    seen = {}
    for c in range(4096):
        cx, cy = c % 64, c // 64
        node = w(ram, CELLS + c * 4 + 2)
        prev = 0
        n = 0
        while node:
            n += 1
            if n > NENT:
                bad.append(("cycle", cx, cy))
                break
            r = ENT + (node - 0x10000 if node & 0x8000 else node)
            if record_of(r) is None or r == ENT:
                bad.append(("not a record", cx, cy, hex(node)))
                break
            if w(ram, r + 4) != prev:
                bad.append(("prev", cx, cy, hex(node), hex(w(ram, r + 4)), hex(prev)))
            if (ram[r + xo], ram[r + yo]) != (cx, cy):
                bad.append(("cell", cx, cy, hex(node), ram[r + xo], ram[r + yo]))
            seen[node] = seen.get(node, 0) + 1
            prev, node = node, w(ram, r + 2)
    live = [(a - ENT) & 0xFFFF for _, base, size, n in ARRAYS
            for a in range(base, base + size * n, size) if a != ENT and ram[a + 12]]
    unlinked = [hex(o) for o in live if seen.get(o, 0) != 1]
    return live, seen, bad, unlinked


def main():
    ram, _ = load_ram(sys.argv[1])
    live, seen, bad, unlinked = check(ram)
    by = {}
    for o in live:
        k = record_of(ENT + (o - 0x10000 if o & 0x8000 else o))
        by[k] = by.get(k, 0) + 1
    print(f"live records (side byte != 0): {len(live)} {by}; nodes in cell lists: {len(seen)}")
    print(f"list faults: {len(bad)}  {bad[:5]}")
    print(f"live records in exactly one list: {len(live) - len(unlinked)}/{len(live)}  {unlinked[:10]}")
    _, _, cbad, _ = check(ram, 7, 9)
    print(f"control (cell from bytes 7/9): list faults {len(cbad)}")
    if "--dump" in sys.argv:
        for o in live:
            if not (0 < o < ESZ * NENT):
                continue
            r = ENT + o
            print(f"{o:04x} side {ram[r+12]:02x} pos ({w(ram,r+6):04x},{w(ram,r+8):04x}) "
                  f"str {l(ram,r+26)} +10 {w(ram,r+10):04x} +18 {ram[r+18]:02x} +22 {ram[r+22]:02x} "
                  f"raw {ram[r:r+ESZ].hex()}")


if __name__ == "__main__":
    main()
