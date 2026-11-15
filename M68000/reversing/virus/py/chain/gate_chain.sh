#!/bin/bash
# Gate: a 2-game natural attract chain from demo/S1b.snap (one REPL, no ESC, no poke) reproduces the first two games of the six-game run
# (over-ticks 12088/12894, scores 17526/19770, wave 3 and 3) and the carried wave $32a52, from a FRESH run (about 5 minutes).  Needs
# scratchpad/virus/demo/S1b.snap (bash reversing/virus/py/demo/capture.sh).  Data: $W/chain/gate/.  Argument "long <games>": a long chain
# in $W/chain/long/ instead (about 2.5 minutes a game), then the table, the start-to-start RAM diff and the byte trends.
cd "$(dirname "$0")/../../../.." || exit 1
W=${VIRUS_WORK:-scratchpad/virus}; P=reversing/virus/py/chain
if [ "$1" = long ]; then
  O=$W/chain/long; rm -rf $O; mkdir -p $O
  uv run python $P/chain.py $W/demo/S1b.snap ${2:-24} $O/chain.jsonl main > $O/chain.log || exit 1
  uv run python $P/table.py $O/chain.jsonl | tee $O/table.txt
  uv run python $P/startdiff.py $O/starts main > $O/startdiff.txt; uv run python $P/trend_bytes.py $O/starts main > $O/trend_bytes.txt
  exit 0
fi
O=$W/chain/gate; rm -rf $O; mkdir -p $O
echo "== 2-game chain from S1b (one lineage, nothing poked)"
uv run python $P/chain.py $W/demo/S1b.snap 2 $O/chain.jsonl gate > $O/chain.log || exit 1
uv run python $P/table.py $O/chain.jsonl | head -3
uv run python $P/check_chain.py $O/chain.jsonl
echo "-- control"; uv run python $P/check_chain.py $O/chain.jsonl --control
