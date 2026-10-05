#!/bin/sh
# gates.sh: fresh runs of the kind-0 gates, then every check. Output dumps go to $AI_OUT (default scratchpad/finalfight/p3/a/out).
#   g1 = idle with Cody's health topped up (FF_GOD=1); f1..f3 = pseudo-random Cody inputs (mkkeys.py seeds 1-3); r1 = $3c26 breakpoint log.
here=$(cd "$(dirname "$0")" && pwd)
root=$(cd "$here/../../../.." && pwd)
out=${AI_OUT:-$root/scratchpad/finalfight/p3/a/out}; export AI_OUT=$out
cd "$here" || exit 1
if [ "$1" != "check" ]; then
  FF_GOD=1 ./run_ai.sh rec g1 ff_enemies 6150 "" >/dev/null 2>&1
  for s in 1 2 3; do FF_GOD=1 ./run_ai.sh rec f$s ff_enemies 6300 "$(python3 mkkeys.py 4160 6200 $s)" >/dev/null 2>&1; done
  FF_LOG=1 ./run_ai.sh hit r1 ff_enemies 6150 "3c56" "" >/dev/null 2>&1
fi
B="$out/g1.bin $out/f1.bin $out/f2.bin $out/f3.bin"
echo '== counters.py'; python3 counters.py $B
echo '== dmgcheck.py'; python3 dmgcheck.py $B
echo '== slotcheck.py'; python3 slotcheck.py $B
echo '== hist.py'; python3 hist.py $B
echo '== animstate.py'; python3 animstate.py $B
echo '== rngcheck.py'; python3 rngcheck.py "$out/r1_log.txt"
