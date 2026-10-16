#!/bin/bash
# run_pool.sh: hits census of the $54 loop and a capture of natural $15ada entries for each pool snapshot, one emulator at a time.
set -u
ROOT=$(d=$(cd "$(dirname "$0")" && pwd); while [ ! -f "$d/tools/rdis.py" ]; do d=$(dirname "$d"); done; echo "$d")
cd "$ROOT"
W=${PM_WORK:-scratchpad/pm162}/merchant
H=$(seq 1 30 | paste -sd, -)
for s in scratchpad/pm148/arms/long/L2G_k124_c8.snap scratchpad/pm148/arms/long/L2G_k88_c3.snap \
         scratchpad/pm148/arms/long/W5G_k80_c1.snap scratchpad/pm148/arms/long/M2G_k30_c5.snap; do
  n=$(basename "$s" .snap)
  printf 'disk scratchpad/powermonger.st\nhits 150000000 15ad2 15ada 15b00 15b14 15b1c 15b54 6522\nq\n' |
    ATARI_NOTRACE=1 dotnet exec bin/Debug/net8.0/M68000.dll resume "$s" repl > "$W/hits_$n.out" 2>&1
  uv run python tools/capture_hits.py "$s" 15ada "$H" "$W/cap" --name "$n" --max 40000000 > "$W/cap_$n.out" 2>&1
done
echo done
