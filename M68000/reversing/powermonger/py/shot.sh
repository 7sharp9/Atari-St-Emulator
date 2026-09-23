#!/bin/bash
# shot.sh <snap> <out.png> (run from M68000/)  -- PM uses direct-to-shifter base $ffff8201/8203
mkdir -p ${PM_WORK:-scratchpad/pmwork}
SNAP=$1; OUT=$2
DISK=scratchpad/powermonger.st
printf 'm ffff8201 1\nm ffff8203 1\nm ffff8205 1\nm ffff8240 32\nq\n' > ${PM_WORK:-scratchpad/pmwork}/_pmd.txt
INFO=$(ATARI_NOTRACE=1 dotnet exec bin/Debug/net8.0/M68000.dll resume "$SNAP" repl --disk-a "$DISK" < ${PM_WORK:-scratchpad/pmwork}/_pmd.txt 2>/dev/null | grep -E '^[0-9a-f]{2}( |$)')
HI=$(echo "$INFO" | sed -n '1p' | tr -d ' ')
MID=$(echo "$INFO" | sed -n '2p' | tr -d ' ')
LO=$(echo "$INFO" | sed -n '3p' | tr -d ' ')
echo "$INFO" | tail -1 > ${PM_WORK:-scratchpad/pmwork}/_pmpal.txt
BASE="${HI}${MID}${LO}"
printf "m $BASE 32000\nq\n" > ${PM_WORK:-scratchpad/pmwork}/_pms.txt
ATARI_NOTRACE=1 dotnet exec bin/Debug/net8.0/M68000.dll resume "$SNAP" repl --disk-a "$DISK" < ${PM_WORK:-scratchpad/pmwork}/_pms.txt 2>/dev/null | grep -E '^[0-9a-f]{2}( |$)' | tail -1 > ${PM_WORK:-scratchpad/pmwork}/_pmscr.txt
python3 tools/screendump.py --rez 0 --screen ${PM_WORK:-scratchpad/pmwork}/_pmscr.txt --palette ${PM_WORK:-scratchpad/pmwork}/_pmpal.txt --out "$OUT" --scale 2
echo "$OUT base=$BASE"
