#!/bin/bash
# watch the first group's owner word of the side (slot + 28, slot = $51538 + side*$13c) to time $2776's clear at $28ae
HERE=$(cd "$(dirname "$0")" && pwd); ROOT=${M68000_ROOT:-$HERE}
while [ ! -f "$ROOT/tools/rdis.py" ]; do ROOT=$(dirname "$ROOT"); [ "$ROOT" = / ] && { echo "no repo root"; exit 1; }; done
cd "$ROOT" || exit 1
D=${PM_WORK:-scratchpad/pm156}/pending/runs; mkdir -p "$D"
run() { printf 'disk scratchpad/powermonger.st\nwatch %s 2\nhits %s 2776 28ae\nq\n' $3 $4 > $D/$1_g0.repl
  ATARI_NOTRACE=1 dotnet exec bin/Debug/net8.0/M68000.dll resume $2 repl < $D/$1_g0.repl > $D/$1_g0.out 2> $D/$1_g0.err; }
run k25 scratchpad/pm143/lands/k25.snap 51a44 30000000
run k60 scratchpad/pm143/lands/k60.snap 517cc 120000000
run k138 scratchpad/pm148/arms/long/M2G_k138_c1.snap 517cc 120000000
run k22 scratchpad/pm148/arms/lands2/k22.snap 51a44 160000000
run k86 scratchpad/pm148/arms/lands2/k86.snap 517cc 120000000
echo done
