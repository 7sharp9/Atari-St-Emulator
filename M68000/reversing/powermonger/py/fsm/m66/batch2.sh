#!/usr/bin/env bash
# batch2.sh: the pre-click wait sweep on k56 and k80 (handoff Open 3): the same sheep clicks after 0..20M steps of
# waiting, 40M steps each, three runs at a time. A natural $66 needs a Boat chaser landing before the first
# slaughter, or a lead vetoed with a reachable order cell; each line of clickrun.sh's summary counts arrivals as
# $66 (arr66), $5106 prev stamps (prev66) and $161f0 water vetoes.
R=$(cd "$(dirname "$0")" && pwd)
n=0
while read l x y; do
  for w in 0 2000000 5000000 10000000 20000000; do
    $R/clickrun.sh $l $x $y $w b2_${l}_${x}_${y}_$w 40000000 &
    n=$((n + 1)); [ $((n % 3)) -eq 0 ] && wait
  done
done <<'L'
k56 26 28
k80 18 85
k80 15 84
L
wait
echo done
