#!/bin/bash
# waveend.sh: tick ($32a44) and wave ($32a50) at each wave completion ($20fb4) in game 1, against the read rule that a wave ends
# when no pool record still has the $21ae2 wait behaviour (last $21ae2 life: wave 0 3000, wave 1 2500, wave 2 2550, wave 3 2700).
cd "$(dirname "$0")/../../../.."
# chain start snapshots: W/chain/long/starts (gate_chain.sh long 24) or the overseer copy that produced the doc's numbers
ST=scratchpad/virus/chain/long/starts; [ -d "$ST" ] || ST=scratchpad/overseer/virus_long/work/main/starts
mkdir -p scratchpad/virus/scan
S=$ST/main_g001.snap
c="m 32a44 2\nm 32a50 2\nm 32a3e 2\n"
printf "m 32a44 2\nbp 20fb4 300000000\n${c}bp 20fb4 300000000\n${c}bp 20fb4 300000000\n${c}bp 20fb4 300000000\n${c}q\n" | ATARI_NOTRACE=1 dotnet exec bin/Debug/net8.0/M68000.dll resume $S repl > scratchpad/virus/scan/waveend.out 2>&1
echo rc=$?
