"""Group the $2df84 writes of seed_watch.sh into bursts (draws less than 200k steps apart).

Usage: seed_bursts.py <watch_out.txt> <watch.txt>
The watch counter is the snapshot's cumulative step count; the run's own `hits 5000000 12c9a`
line gives the first draw in run steps, which fixes the offset.
"""
import re
import statistics
import sys

out, watch = open(sys.argv[1]).read(), open(sys.argv[2]).read()
first_run = int(re.search(r"\$012c9a\s+\d+\s+first (\d+)", out).group(1))
draws = [int(m) for m in re.findall(r"step=(\d+) pc=\S+ WriteWord \$0002df84", watch)]
off = draws[0] - first_run
draws = [s - off for s in draws]
bursts = [[draws[0]]]
for s in draws[1:]:
    (bursts[-1].append(s) if s - bursts[-1][-1] < 200_000 else bursts.append([s]))
gaps = [b[0] - a[0] for a, b in zip(bursts, bursts[1:])]
print(f"{len(draws)} draws in {len(bursts)} bursts, run steps {draws[0]:,} .. {draws[-1]:,}")
print(f"gap between bursts: median {statistics.median(gaps):,.0f}, min {min(gaps):,}, max {max(gaps):,}")
print(f"draws per burst: median {statistics.median(len(b) for b in bursts)}, max {max(len(b) for b in bursts)}")
