#!/usr/bin/env bash
# The forced posture-5 trade run forward: does the posture or the trade's byte-44 codes change the fight?
# State: trade5.sh's at63f4.snap with its x pokes (lord 15 byte 0 := 3, lord 14 byte 25 := 5). 2x2 arms:
# posture word $51974 := 5|3 at $63f4, crossed with byte 44 of the 12 men $53b6e + 50k (k = 0..11) left as the
# trade wrote it or poked at the rts $6500 to the other arm's values (posture 5 writes $84 to k 0..8 and $92 to
# k 9..11 at $63e8; posture 3 leaves 0; bytes 45..47 are 5a 00 00 in both, so the longword pokes keep them).
# Each arm runs 6 x 10M steps counting melee $1536e/$1537a, kill $5590, the rout roll $3110 and the tick $6522,
# snapshots at 30M and 60M, and trade5_census.py counts men per side and the 12 men's health.
# Then `drain`: from the posture-3 arm with the $84/$92 pokes, 60 stops at $15380 (sub.b D0,45(A3)), D0 by attacker.
#   trade5_fwd.sh           (from anywhere; repo root found via tools/rdis.py)
# Output: ${PM_WORK:-scratchpad/pm163}/p5fwd/{x_<arm>.out,x_<arm>_{30,60}.snap/.ram,drain.out}
set -e
HERE=$(cd "$(dirname "$0")" && pwd); d=$HERE
while [ ! -f "$d/tools/rdis.py" ]; do d=$(dirname "$d"); done
cd "$d"
O=${PM_WORK:-scratchpad/pm163}/p5fwd; mkdir -p "$O"
S=${TRADE_SNAP:-scratchpad/pm162/posture/trade/at63f4.snap}
[ -f "$S" ] || { echo "no $S: run trade5.sh first" >&2; exit 1; }
run() { ATARI_NOTRACE=1 dotnet exec bin/Debug/net8.0/M68000.dll resume "$S" repl; }
pre() {  # $1 = posture, $2 = b84|b0|keep
  echo 'disk scratchpad/powermonger.st'; echo "w 51974 000${1}0002"; echo 'w 4e6f4 03000000'; echo 'w 4e6ec 00050000'
  echo 'bp 6500 400000'
  for k in $(seq 0 11); do
    case $2 in b84) v=845a0000; [ "$k" -ge 9 ] && v=925a0000;; b0) v=005a0000;; *) continue;; esac
    echo "w $(printf %x $((0x53b6e + 50 * k + 44))) $v"
  done
}
for arm in P5B84 P3B0 P3B84 P5B0; do
  case $arm in P5B84) a='5 keep';; P3B0) a='3 keep';; P3B84) a='3 b84';; P5B0) a='5 b0';; esac
  { pre $a; for i in 1 2 3 4 5 6; do echo 'hits 10000000 1536e 1537a 5590 3110 6522'; echo 'm 51974 2'
      [ $i = 3 ] && echo "snap $O/x_${arm}_30.snap"; done
    echo "snap $O/x_${arm}_60.snap"; echo q; } | run > "$O/x_$arm.out" 2>&1 &
done
{ pre 3 b84; for i in $(seq 60); do echo 'bp 15380 40000000'; done; echo q; } | run > "$O/drain.out" 2>&1 &
wait
uv run python reversing/powermonger/py/snap2ram.py "$O"/x_*_[36]0.snap > /dev/null
for arm in P5B84 P3B0 P3B84 P5B0; do
  echo "== $arm"; grep -E '^  \$' "$O/x_$arm.out" | awk '{printf "%s=%s ", $1, $2} NR % 5 == 0 {print ""}'
done
uv run python "$HERE/trade5_census.py" "$O"/x_*_30.ram "$O"/x_*_60.ram
# drain: pair each $15380 stop's D0 with its A1 (only dumps that follow a $15380 stop).
grep -A8 'breakpoint $00015380' "$O/drain.out" | grep -E '^D0|^A0' | paste - - |
  awk '{print substr($1, 10, 2), substr($6, 4)}' | uv run python -c "
import sys, collections
men = {0x53b6e + 50 * k for k in range(12)}
c = collections.Counter()
for l in sys.stdin:
    dd, a = l.split(); c[('trade man' if int(a, 16) in men else 'other', '\$' + dd)] += 1
print('drain D0 by attacker:', dict(sorted(c.items())))"
