#!/bin/bash
# The computer god's power stage $25a32 per kind, over a long unpoked run from battle start snapshots made by
# battle_census.sh (<dir>/b<N>_start.snap). `hits` over STEPS steps (default 300,000,000) on: the stage $25a32, the
# mana-short exit $25ae2, the kind dispatch $25aea, the kind entries (table $25b00: kind 0 and $a $25b0c, kind 2
# $25b16, kind 4 $25b28, kind 6 $25b36, kind 8 $25b44), the post $25b5e and the executed commands $292e4.
# Run from M68000/:  bash reversing/populous2/py/god/power_census.sh [dir] [steps] [battle ...]
set -e
cd "$(dirname "$0")/../../../.."
DIR=${1:-scratchpad/populous2/battle}
STEPS=${2:-300000000}
shift 2 2>/dev/null || shift $#
BATTLES=${*:-10 40 100}
ADDRS="25a32 25ae2 25aea 25b0c 25b16 25b28 25b36 25b44 25b5e 292e4"
for n in $BATTLES; do
  { echo "hits $STEPS $ADDRS"; echo "snap $DIR/b${n}_end.snap"; echo q; } \
    | ATARI_NOTRACE=1 dotnet exec bin/Debug/net8.0/M68000.dll resume "$DIR/b${n}_start.snap" repl > "$DIR/p$n.log" 2>&1 &
done
wait
for n in $BATTLES; do
  awk -v n="$n" '/^  \$0/ { c[$1] = $2 }
    END { printf "battle %s: stage %d mana-short %d dispatch %d kind0/a %d kind2 %d kind4 %d kind6 %d kind8 %d post %d; commands %d\n",
          n, c["$025a32"], c["$025ae2"], c["$025aea"], c["$025b0c"], c["$025b16"], c["$025b28"], c["$025b36"], c["$025b44"],
          c["$025b5e"], c["$0292e4"] }' "$DIR/p$n.log"
done
