#!/usr/bin/env python3
"""Print the REPL `w` line that sets bytes in RAM while keeping the other bytes of
the (even-aligned) longword, read from a RAM image of the poke point.
  uv run python pokew.py <ram> <addr>=<hexbytes> [...]
  e.g. pokew.py cap/ctl_0.ram 51beb=08      -> w 51bea 00080012
       pokew.py cap/ctl_0.ram 51c9a=ffec    (word 14 of $51c92 := -$14)
REPL `w` writes a longword (an odd address kills the REPL), so each poke is
rounded down to an even address and widened to 4 bytes; a poke that would span
two longwords prints two lines. Comment lines name old -> new."""
import sys
from pathlib import Path

ram = bytearray(Path(sys.argv[1]).read_bytes())
new = bytearray(ram)
touched = set()
for spec in sys.argv[2:]:
    a, v = spec.split("=")
    a = int(a, 16)
    bs = bytes.fromhex(v)
    new[a:a + len(bs)] = bs
    for i in range(len(bs)):
        touched.add((a + i) & ~1)
# one longword per run of touched bytes, each starting at an even address
starts = []
for t in sorted(touched):
    if not starts or t >= starts[-1] + 4:
        starts.append(t)
for s in starts:
    print(f"# ${s:05x}: {ram[s:s+4].hex()} -> {new[s:s+4].hex()}")
    print(f"w {s:x} {new[s:s+4].hex()}")
