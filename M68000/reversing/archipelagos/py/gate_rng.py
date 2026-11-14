#!/usr/bin/env python3
"""gate_rng.py <log>: the island RNG $16622 is s = 5*s + 1 (mod 65536). Reads a REPL `watch 16978` log (stderr)
and counts successive written seeds that obey it. Prints N/N, and the same count for the broken form s = 5*s + 2.
Default log: scratchpad/archipelagos/blood/rng_log.txt (py/capture_islands.sh)."""
import os, re, sys
d = os.path.abspath(os.path.dirname(__file__))
while not os.path.exists(os.path.join(d, 'tools', 'rdis.py')):
    d = os.path.dirname(d)
path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(d, 'scratchpad', 'archipelagos', 'blood', 'rng_log.txt')
L = [int(re.search(r'<- \$([0-9a-f]+)', l).group(1), 16) for l in open(path)]
assert len(L) > 100, f'{path}: only {len(L)} writes'
for name, add in (('model s=5s+1', 1), ('broken control s=5s+2', 2)):
    ok = sum(((5 * a + add) & 0xFFFF) == b for a, b in zip(L, L[1:]))
    print(f'{name}: {ok}/{len(L) - 1}')
