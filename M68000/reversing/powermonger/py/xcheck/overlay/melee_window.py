#!/usr/bin/env python3
"""Parse the WATCH lines of real_melee84.sh's men watch (records $53b6e + 50k, k = 0..11):
writers per record offset, the byte-31 values written, and the melee ($32/$34) writes with
their cumulative step, which is the window a capture must land in.
  uv run python <this> <watch.err>"""
import collections, re, sys

pat = re.compile(r'step=(\d+) pc=\$([0-9a-f]+) Write(\w+) \$([0-9a-f]+) <- \$([0-9a-f]+)')
offs, b31 = collections.Counter(), []
for line in open(sys.argv[1]):
    m = pat.search(line)
    if not m:
        continue
    st, pc, w, a, v = int(m[1]), m[2], m[3], int(m[4], 16), int(m[5], 16)
    k, o = divmod(a - 0x53b6e, 50)
    n = {'Byte': 1, 'Word': 2, 'Long': 4}[w]
    offs[(o, w, pc)] += 1
    if o <= 31 < o + n:
        b31.append((st, k, (v >> (8 * (o + n - 1 - 31))) & 0xff, pc))
for (o, w, pc), c in sorted(offs.items()):
    print(f"off {o:2} {w:4} pc ${pc} x{c}")
print("offset 44 writes:", sum(c for (o, _, _), c in offs.items() if o <= 44 < o + 2))
print("byte 31 values:", dict(collections.Counter(f"${v:02x}" for _, _, v, _ in b31)))
mel = [t for t in b31 if t[2] in (0x32, 0x34)]
if mel:
    print(f"melee writes {len(mel)}, steps {mel[0][0]}..{mel[-1][0]}, men {sorted({t[1] for t in mel})}")
