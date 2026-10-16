#!/usr/bin/env bash
# class_a.sh [chunks] [steps]: opponent class $a ($4de2 arm $4eca, categories $14/$16) reached through the player's sword click
# on k120's lone sheep, by a labelled one-byte poke of the sheep's category.  Start: nat/n4a7a_k120_a_1.snap (capture_clicks.sh:
# the click's own $4a7a entry, D0 = 31, D1 = 78; the sheep is record $4ceca, bytes 4..7 = 00 08 08 11).  Three arms, same
# snapshot, same budget:
#   ctl  no poke                                  (category 8: class 8, the chase $50da / mode $36)
#   p16  w 4cece 00081611  byte 6 $08 -> $16      (a forest-marker category)
#   p14  w 4cece 00081411  byte 6 $08 -> $14      (a carrier-pigeon category)
# Each: `hits` per chunk on the march/arrival/classifier/picker arms, the group's state 0(A3), 24, 204, 216 and the sheep's
# bytes 4..7 per chunk, a snapshot per chunk.  Output under ${PM_WORK:-scratchpad/pm162}/g4a7a/classa/.
set -e
HERE=$(cd "$(dirname "$0")" && pwd)
ROOT=${M68000_ROOT:-$HERE}
while [ ! -f "$ROOT/tools/rdis.py" ]; do ROOT=$(dirname "$ROOT"); [ "$ROOT" = / ] && { echo "no repo root"; exit 1; }; done
cd "$ROOT"
W=${PM_WORK:-scratchpad/pm162}/g4a7a
D=$W/classa; mkdir -p "$D"
SNAP=$W/nat/n4a7a_k120_a_1.snap
n=${1:-8}; steps=${2:-2000000}
A="4a7a 4b30 1519e 4bc8 4de2 4eb6 4eca 4d40 4dae 4f68 50da 5100 5150 153cc 1547e 531c 57f0 596a 4624 6522"
for arm in ctl p16 p14; do
  {
    echo "disk scratchpad/powermonger.st"
    case $arm in p16) echo "w 4cece 00081611" ;; p14) echo "w 4cece 00081411" ;; esac
    echo "m 4cece 4"
    for i in $(seq 1 "$n"); do
      echo "hits $steps $A"
      echo "m 516c0 2"; echo "m 516d8 2"; echo "m 5178c 2"; echo "m 51798 2"; echo "m 4cece 4"
      echo "snap $D/${arm}_c$i.snap"
    done
    echo q
  } > "$D/$arm.cmds"
  echo "uptime: $(uptime)" > "$D/$arm.txt"
  ATARI_NOTRACE=1 dotnet exec bin/Debug/net8.0/M68000.dll resume "$SNAP" repl < "$D/$arm.cmds" 2>&1 | grep -v "first -1" >> "$D/$arm.txt"
  echo "== $arm done"
done
