#!/usr/bin/env bash
# batch1.sh: the 10 sheep-click sites of the 156th pass (cand66.py candidates), 40M steps each.
R=$(cd "$(dirname "$0")" && pwd)
while read l x y; do $R/clickrun.sh $l $x $y 0 b1_${l}_${x}_${y} 40000000; done <<'L'
k116 40 23
k12 29 66
k143 16 102
k143 12 106
k32 31 3
k32 27 23
k8 17 0
k80 18 85
k80 15 84
k16 31 63
L
echo done
