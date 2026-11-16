#!/usr/bin/env python3
"""captain_trace.py <man offset hex> <run dir> ...: one leader-flag man over a loop.py --objs replay (<run dir>/objs.bin).
`$550e` turns a captain into a new group's lead only when it finds him with owner > 0, flag bit 4 and mode (byte 31)
`$8a` (resting at his town) or `$3c` (routed home outside a group), and `$5c2c` only when he leads no group that still
has members (README "A second side-1 group"; economy.md section 3). Per run: the samples, his modes while alive, the
number of samples in a candidate mode and their first and last step, the followers (live men whose word 28 is his
offset) at those samples, and the step his owner first goes to 0 or below. Samples are EVERY steps apart (1e5 is about
0.6 tick), so a window shorter than that can be missed; the lord's side is not in objs.bin."""
import struct, sys, zlib
from collections import Counter
from pathlib import Path

man = int(sys.argv[1], 16)
CAND = (0x8a, 0x3c)


def sb(v):
    return v - 256 if v > 127 else v


def samples(path):
    b = Path(path).read_bytes(); i = 0
    while i < len(b):
        step, n = struct.unpack_from('<QI', b, i); i += 12
        yield step, zlib.decompress(b[i:i + n]); i += n


tot = Counter()
for run in sys.argv[2:]:
    n = 0; modes = Counter(); cand = []; dead = None; foll = Counter(); last = None
    for step, R in samples(Path(run) / 'objs.bin'):
        n += 1; r = R[man:man + 50]; last = step
        if sb(r[5]) <= 0 or not r[7] & 0x10:
            if dead is None:
                dead = step
            continue
        modes[r[31]] += 1
        if r[31] in CAND:
            f = sum(1 for i in range(512) if sb(R[i * 50 + 5]) > 0 and R[i * 50 + 6] == 0
                    and struct.unpack_from('>H', R, i * 50 + 28)[0] == man)
            cand.append((step, r[31], f, struct.unpack_from('>H', r, 42)[0])); foll[f] += 1
    tot['runs'] += 1; tot['samples'] += n; tot['cand_samples'] += len(cand); tot['runs_cand'] += bool(cand)
    tot['runs_dead'] += dead is not None
    top = ' '.join('$%02x:%d' % (m, c) for m, c in modes.most_common(6))
    print('%-34s samples %5d to %5dM | alive %5d | dead at %s | cand %4d %s followers %s | %s' % (
        run[-34:], n, last // 10**6, sum(modes.values()), '%dM' % (dead // 10**6) if dead is not None else '-',
        len(cand), ('%.1fM..%.1fM modes %s 42()=%s' % (cand[0][0] / 1e6, cand[-1][0] / 1e6,
                                                  sorted({'$%02x' % c[1] for c in cand}),
                                                  sorted({'$%04x' % c[3] for c in cand}))) if cand else '',
        dict(foll) if cand else '', top))
print('total:', dict(tot))
