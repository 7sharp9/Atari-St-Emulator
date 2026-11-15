#!/bin/bash
# census.sh: hits census over game 1 of the unpoked chain (main_g001 start, 600M steps: past its game over at ~546M).
# Entry of every pool behaviour, the spawn/transition sites, and the helpers named in behaviours.md.
cd "$(dirname "$0")/../../../.."
# chain start snapshots: W/chain/long/starts (gate_chain.sh long 24) or the overseer copy that produced the doc's numbers
ST=scratchpad/virus/chain/long/starts; [ -d "$ST" ] || ST=scratchpad/overseer/virus_long/work/main/starts
mkdir -p scratchpad/virus/scan
S=$ST/main_g001.snap
A="21776 21792 21894 21976 219de 21ae2 21afe 21c42 21c64 21d08 21df6 21f00 2200c 2202c 22164 221ac 222dc 22316 22486 224a6 22688 226ac 2279a 228de 20206 201b4 25306 20702 206b8 205f6 204d4 2086a 2010a 22e38 22d5e 22ebe 225d6 22722 21764 216d6 20fb4 20e74"
printf 'hits 600000000 %s\nq\n' "$A" | ATARI_NOTRACE=1 dotnet exec bin/Debug/net8.0/M68000.dll resume $S repl > scratchpad/virus/scan/census.out 2>&1
echo rc=$?
