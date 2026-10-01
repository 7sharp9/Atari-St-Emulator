"""rule42.py <snap>...: troops_field vs live men by home lord, three candidate rules:
 A bit6 clear and not leader-flag (the 136th rule); B 42(man)==0 (not in a group); C bit6 clear.
Also the crosstab of (bit6, 42!=0, leader flag) over all live men."""
import collections, os, struct, sys
ROOT = os.environ.get('M68000_ROOT') or os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
from disassemble import ram_from_snap
W = lambda r, a: struct.unpack('>H', r[a:a + 2])[0]
cross = collections.Counter(); score = collections.Counter(); bad = []
for p in sys.argv[1:]:
    r = ram_from_snap(p)
    men = collections.defaultdict(list)
    for i in range(512):
        a = 0x51b66 + 50 * i
        if not (0 < r[a + 5] < 128) or r[a + 6] != 0: continue
        men[W(r, 0x4f916 + W(r, a + 34) + 14)].append(a)
        cross[(bool(r[a + 7] & 0x40), W(r, a + 42) != 0, bool(r[a + 7] & 0x10))] += 1
    for li in range(64):
        b = 0x4e514 + 32 * li
        if r[b] == 0 and W(r, b + 4) == 0: continue
        tf = W(r, b + 8); L = men.get(32 * li, [])
        A = sum(1 for a in L if not r[a + 7] & 0x40 and not r[a + 7] & 0x10)
        B = A + sum(1 for a in L if not r[a + 7] & 0x40 and r[a + 7] & 0x10 and W(r, a + 42) == 0)
        C = sum(1 for a in L if not r[a + 7] & 0x40)
        score['lords'] += 1
        for n, v in (('A', A), ('D', B), ('C', C)):
            score[n + '_exact'] += tf == v; score[n + '_within1'] += abs(tf - v) <= 1
        if tf != B: bad.append((os.path.basename(p), li, tf, A, B, C))
print(dict(score)); print('crosstab (bit6, 42!=0, leaderflag):', dict(cross))
print('D misses (snap, lord, tf, A, D, C):', len(bad), 'of which tf < 1000:', sum(1 for x in bad if x[2] < 1000))
[print(' ', x) for x in bad if x[2] < 1000]
print('snapshots with misses:', sorted(set(x[0] for x in bad))[:12])
