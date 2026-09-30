"""compare_overlays.py: how much of the overlay is shared between levels/disks.  For every overlay .bin found here, take the
header-word tables (table1 potions, table2 spells, table3 timers: offsets as in overlay_map.py), extract the first 16 bytes of each
entry's routine, and report for each table the number of entries whose routine head is identical in all overlays whose header
fits the standard layout, and per overlay the entries that differ.  Standard-layout overlays: one-disk levels 0/1, Disk 2 pairs
0/7/14 (pairs 21/28 have a different first-record layout but the same three tables, so they are included too: only words +2/+4/+6
are used)."""
import glob, struct, os
D = 'scratchpad/cadaver/secrets_out/overlay/'
names = {'overlay_one_pair0': 'one L0', 'overlay_one_pair5': 'one L1', 'overlay_d2_pair0': 'D2 L0', 'overlay_d2_pair7': 'D2 L1', 'overlay_d2_pair14': 'D2 L2', 'overlay_d2_pair21': 'D2 L3', 'overlay_d2_pair28': 'D2 L4'}
ovs = {}
for k in names:
    d = open(D + k + '.bin', 'rb').read()[4:]; ovs[k] = d
W = lambda d, o: struct.unpack_from('>H', d, o)[0]; S = lambda d, o: struct.unpack_from('>h', d, o)[0]
def tables(d):
    t1, t2, t3 = W(d, 2), W(d, 4), W(d, 6)
    n1 = 18; n2 = W(d, t2) // 2; n3 = W(d, t3) // 2
    return [(t1, n1), (t2, n2), (t3, n3)]
def head(d, t, i, n=16):
    a = t + S(d, t + 2 * i); return d[a:a + n]
for ti, label in enumerate(('potions(table1)', 'spells(table2)', 'timers(table3)')):
    cnt = None; rows = {}
    for k, d in ovs.items():
        t, n = tables(d)[ti]
        rows[k] = [head(d, t, i) for i in range(n)]
    n = min(len(v) for v in rows.values())
    ref = rows['overlay_one_pair0']
    same_all = [i for i in range(n) if all(rows[k][i] == ref[i] for k in rows)]
    print('%s: entries %s; identical 16-byte routine heads in all %d overlays: %d of %d' % (label, {names[k]: len(v) for k, v in rows.items()}, len(rows), len(same_all), n))
    for k in rows:
        diff = [i for i in range(min(n, len(rows[k]))) if rows[k][i] != ref[i]]
        print('   %-7s differs from one-disk L0 at entries %s' % (names[k], diff))
