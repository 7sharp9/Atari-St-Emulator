#!/bin/bash
# watches.sh [name...]: the live watches behind stuck_classes.py's 'revived' class (strategy.md "The pending word").
# One emulator at a time, no pokes. Each run writes <name>.repl/.out/.err (WATCH lines) in $PM_WORK/pending/runs.
#   k104a  the -4 pigeon launch: $45a8 writes the dead sender's owner byte into pigeon $4c146 (around step 794.19M)
#   k4     the k4 inheritance: the refilled slot's pending word $51a2e takes no write in 170M steps
#   k32 k124 k25a k25b k60 k138 k22 k86   the revived/unseen lineages: commander record bytes 4..7 (kill at $55f2,
#          revival at $4258/$42ac); k25 watches 26 bytes to also catch word 28 (the group link written at $1b78)
#   k6     a revived/seen case (M2G_k6_c1, record already dead in the start snapshot)
HERE=$(cd "$(dirname "$0")" && pwd); ROOT=${M68000_ROOT:-$HERE}
while [ ! -f "$ROOT/tools/rdis.py" ]; do ROOT=$(dirname "$ROOT"); [ "$ROOT" = / ] && { echo "no repo root"; exit 1; }; done
cd "$ROOT" || exit 1
D=${PM_WORK:-scratchpad/pm156}/pending/runs; mkdir -p "$D"
L=scratchpad/pm148/arms
H='6522 2776 28ae 27c6 4244 42be 5590'
spec() { case $1 in
  k104a) echo "scratchpad/pm143/lands/k104.snap|hits 89000000 2776 28ae 27c6 683e 4562 45a8 4244
snap $D/k104_793.snap
watch 4c146 26
bpc 45a8 1 3000000
r
m 53dc6 50
s 40
m 4c146 26
m 51a2c 2" ;;
  k4)   echo "scratchpad/pm143/lands/k4.snap|watch 51a28 316
hits 170000000 6522 6564 25d6 26d0 2776 27c6 283a 28ae 4220 6b20 683e 4562 45a8 41dc 4244" ;;
  k32)  echo "scratchpad/pm143/lands/k32.snap|watch 54b76 4
hits 250000000 $H" ;;
  k124) echo "scratchpad/pm143/lands/k124.snap|watch 54c0c 4
hits 250000000 $H" ;;
  k25a) echo "scratchpad/pm143/lands/k25.snap|watch 5608e 26
hits 250000000 $H" ;;
  k25b) echo "$L/long/L2G_k25_c1.snap|watch 5608e 26
hits 250000000 $H" ;;
  k60)  echo "scratchpad/pm143/lands/k60.snap|watch 542de 4
hits 250000000 $H" ;;
  k138) echo "$L/long/M2G_k138_c1.snap|watch 53532 4
hits 250000000 $H" ;;
  k22)  echo "$L/lands2/k22.snap|watch 53f28 4
hits 250000000 $H" ;;
  k86)  echo "$L/lands2/k86.snap|watch 54f5e 4
hits 250000000 $H" ;;
  k6)   echo "$L/long/M2G_k6_c1.snap|watch 5459a 4
hits 250000000 $H" ;;
  esac; }
names=${*:-k104a k4 k32 k124 k25a k25b k60 k138 k22 k86 k6}
for n in $names; do
  s=$(spec $n); snap=${s%%|*}; body=${s#*|}
  printf 'disk scratchpad/powermonger.st\n%s\nq\n' "$body" > "$D/$n.repl"
  ATARI_NOTRACE=1 dotnet exec bin/Debug/net8.0/M68000.dll resume "$snap" repl < "$D/$n.repl" > "$D/$n.out" 2> "$D/$n.err"
  echo "$n: $(grep -c WATCH "$D/$n.err") watch lines; revival: $(grep -E 'pc=\$004258|pc=\$0042ac' "$D/$n.err" | head -2 | tr '\n' ' ')"
done
