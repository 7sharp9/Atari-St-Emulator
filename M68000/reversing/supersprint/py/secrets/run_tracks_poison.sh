#!/bin/sh
# runtime poison of the never-consumed candidate blocks of SUPER.DAT on every track (race snapshots snap/race_t<N>.snap, 3M steps each)
cd "$(dirname "$0")/../../../.."  # M68000/
for t in 0 1 2 3 4 5 6 7; do
  python3 reversing/supersprint/py/secrets/runtime_poison.py scratchpad/supersprint/agents/secrets/snap/race_t$t.snap 3000000 \
     28e00,37e00,43e00,4be00,53e00 2ce00,38e00,44e00,4ee00,54e00 1000 track$t > scratchpad/supersprint/agents/secrets/tmp/rp_track$t.log 2>&1
done
