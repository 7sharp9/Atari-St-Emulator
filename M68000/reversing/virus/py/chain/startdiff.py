"""startdiff.py <starts dir> <tag> [lo hi]: RAM diff of successive demo-start snapshots (<tag>_gNNN.snap) of one lineage.
Reads RAM straight from the snapshot (RAM at file offset 87, 1 MiB; offset checked against the RNG bytes of the first snapshot).
Excludes the stack ($6e000..$6ffff by default) and the screens/buffers ($52a58..$6dfff).  Prints, per consecutive pair, the number of
differing bytes outside the exclusions, and at the end the table of bytes that differ in the most pairs (with first/last value and
the number of distinct values), the region names from classify.py, and the bytes that differ in every pair."""
import sys, os, glob, collections
d, tag = sys.argv[1], sys.argv[2]
OFF = 87; EXC = [(0x6e000, 0x70000), (0x52a58, 0x6e000)]
files = sorted(glob.glob(os.path.join(d, f'{tag}_g*.snap')))
def ram(f):
    b = open(f, 'rb').read(); return b[OFF:OFF + 0x100000]
REG = [(0x2706e, 0x27076, 'RNG'), (0x27134, 0x2714c, 'target queue $27134'), (0x25ccc, 0x25de4, 'high-score table'), (0x2708e, 0x270a1, 'score block'),
       (0x270a2, 0x270b0, 'pilot state'), (0x270b0, 0x270d4, 'ship'), (0x31d54, 0x32a2e, 'pool'), (0x32a58, 0x42a58, 'object map'), (0x42a58, 0x52a58, 'height map'),
       (0x32a2e, 0x32a58, 'game words $32a2e..'), (0xc000, 0x27000, 'code/tables'), (0x27000, 0x31d54, 'variables'), (0x400, 0xc000, 'low RAM/TOS')]
def name(x):
    for s, e, n in REG:
        if s <= x < e: return n
    return 'other'
def excl(x): return any(s <= x < e for s, e in EXC)
prev = ram(files[0]); cnt = collections.Counter(); vals = collections.defaultdict(set); first = {}; last = {}
for k, f in enumerate(files[1:], 2):
    cur = ram(f); n = 0
    for i in range(len(cur)):
        if cur[i] != prev[i] and not excl(i):
            n += 1; cnt[i] += 1; vals[i].add(cur[i]); first.setdefault(i, (k, prev[i])); last[i] = (k, cur[i])
    print(f'start {k-1} -> {k}: {n} bytes differ outside stack/screens'); prev = cur
npairs = len(files) - 1
print(f'\n{npairs} consecutive pairs; bytes that differ, by region (byte count, of which in every pair):')
reg = collections.defaultdict(lambda: [0, 0])
for i, c in cnt.items(): reg[name(i)][0] += 1; reg[name(i)][1] += (c == npairs)
for n, (a, b) in sorted(reg.items(), key=lambda t: -t[1][0]): print(f'  {n:24s} {a:6d} {b:6d}')
print('\nbytes differing in >= half of the pairs, grouped (addr, pairs, distinct values, first->last):')
rows = sorted(i for i, c in cnt.items() if c * 2 >= npairs)
grp = []
for i in rows:
    if grp and i - grp[-1][-1] <= 2: grp[-1].append(i)
    else: grp.append([i])
for g in grp[:200]:
    print(f'  ${g[0]:06x}..${g[-1]:06x} ({len(g)}B, {name(g[0])}): pairs {min(cnt[i] for i in g)}-{max(cnt[i] for i in g)}, distinct up to {max(len(vals[i]) for i in g)}')
print(len(grp), 'groups')
