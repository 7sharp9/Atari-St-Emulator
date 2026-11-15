#!/bin/bash
# watch_deep.sh: every write into the deep part of bucket 2 ($29703..$29770, one of the six "monotone" blocks) over game 1
# of the chain (main_g001 start to past its game over, 600M steps). Positive control: the block goes 00 -> 83.. by g002.
cd "$(dirname "$0")/../../../.."
# chain start snapshots: W/chain/long/starts (gate_chain.sh long 24) or the overseer copy that produced the doc's numbers
ST=scratchpad/virus/chain/long/starts; [ -d "$ST" ] || ST=scratchpad/overseer/virus_long/work/main/starts
mkdir -p scratchpad/virus/scan
S=$ST/main_g001.snap
printf 'watch 29703 $6e\ns 600000000\nm 29700 112\nq\n' | ATARI_NOTRACE=1 dotnet exec bin/Debug/net8.0/M68000.dll resume $S repl > scratchpad/virus/scan/watch_deep.out 2> scratchpad/virus/scan/watch_deep.err
echo rc=$?
