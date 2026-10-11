"""fdc_sectors.py <log> [spt]  summarise the ATARI_TRACE_FDC=1 sector lines of a run log.
Logical sector = track*spt + sector-1 (single-sided; default spt 10, the save-disk geometry).
Prints, per direction, the count, failures, the side set, the logical range and whether it is
contiguous, plus the DMA range; and every Type II command whose status was not $00."""
import re, sys
log, spt = sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 10
L = open(log, errors='replace').read().splitlines()
pat = re.compile(r"FDC (read |write) drive=(\d) track=(\d+) side=(\d) sector=(\d+) dma=\$(\w+) -> (.*)")
runs = {}
for l in L:
    m = pat.match(l)
    if m:
        k, d, t, s, sec, dma, res = m.groups()
        runs.setdefault(k.strip(), []).append((int(t) * spt + int(sec) - 1, int(s), int(dma, 16), res))
for k, v in runs.items():
    secs = [x[0] for x in v]
    bad = [x for x in v if x[3] != 'OK']
    # split into maximal contiguous runs
    groups = []; 
    for s_, _, dma, _ in v:
        if groups and s_ == groups[-1][1] + 1: groups[-1][1] = s_; groups[-1][3] = dma
        else: groups.append([s_, s_, dma, dma])
    print(f"{k}: {len(v)} sectors, failed {len(bad)}, sides {sorted(set(x[1] for x in v))}")
    for a, b, d0, d1 in groups:
        print(f"   logical {a}..{b} ({b-a+1} sectors)  dma ${d0:06x}..${d1+512:06x}")
for l in L:
    if l.startswith('FDC cmd') and 'SECTOR' in l and 'status=$00' not in l: print('  ', l)
