"""Where the pilot's thrust is spent, from the 120-tick approach windows of every death (ticks with fuel > 0 only).
vy is the ship's vertical velocity word (+ = down); clearance = ground - $56 - y from the $257f4 reading (+ = above ground)."""
import sys; sys.argv = sys.argv[:1]
import aggregate as A, collections
bins = collections.Counter(); asked = collections.Counter(); n = 0
cl = collections.Counter(); clasked = collections.Counter()
for r in A.rows:
    T = r['d'].get('approach', {}).get('ticks') or []
    for t in T:
        if t['fuel'] <= 0: continue
        vy = t['ship'][4]; b = min(max(vy // 50, -4), 5) * 50
        bins[b] += 1; n += 1
        a = bool(t['d'][2] & 2)
        asked[b] += a
        if t['gnd'] is not None:
            c = t['gnd'] - 0x56 - t['ship'][1]; k = min(c // 500, 8) * 500
            cl[k] += 1; clasked[k] += a
print('ticks with fuel>0 in the windows:', n)
print('vy bin (>=)   ticks  thrust asked   share of all thrust-asked ticks')
tot = sum(asked.values())
for b in sorted(bins): print(f'{b:6d} {bins[b]:8d} {asked[b]/bins[b]:8.2f} {asked[b]/tot:8.2f}')
print('clearance bin (>=)  ticks  thrust asked')
for k in sorted(cl): print(f'{k:6d} {cl[k]:8d} {clasked[k]/cl[k]:8.2f}')
