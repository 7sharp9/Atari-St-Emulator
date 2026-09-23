#!/usr/bin/env bash
# run from M68000/; output in $PM_WORK/run; EXTRA="addr ..." adds addresses
# runland.sh <src.snap> <name> <stretches> <steps>: run forward in stretches, PC-hit census + snapshot per stretch
src=$1; name=$2; n=$3; steps=$4
d=${PM_WORK:-scratchpad/pmwork}/run; mkdir -p $d
A="$EXTRA 6522 661a 68fe 68ee 6a3a 15302 56a6 5778 5590 55f2 560a 5bd2 5c10 57f0 1d70 25d6 4bc8 5c80 1623c 162c8 162d8 2776 1b8c 3c08 5cde 550e 638c 61f8 60dc 159de 159a4 3ac8 45f2 15462 5e3a 163b8"
{ for i in $(seq 1 $n); do echo "hits $steps $A"; echo "snap $d/${name}_s$i.snap"; done; echo q; } > $d/$name.cmds
ATARI_NOTRACE=1 dotnet exec bin/Debug/net8.0/M68000.dll resume $src repl --disk-a scratchpad/powermonger.st < $d/$name.cmds > $d/$name.txt 2>&1
