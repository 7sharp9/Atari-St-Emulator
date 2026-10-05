#!/bin/sh
# make_proof_dumps.sh: the dump sets prove.py reads (about 40 s). Needs run/sta/ffightuc/{ff_gameplay,ff_enemies,
# sb_boss1,sb_stage1,sb_stall2}.sta (copy them there from the states the earlier passes saved).
here=$(cd "$(dirname "$0")" && pwd)
run() { sh "$here/run_dump.sh" "$1" "$2" "$3" 400; }
run ff_gameplay gp 4
run ff_enemies en 2
run sb_boss1 bo 2
run sb_stage1 s1 2
run sb_stall2 st2 2
# one layer at a time: poke the layer-control pipeline words 110(A5) and 112(A5) ($ff806e, $ff8070)
for t in "L0 12c0" "L1 12c2" "L2 12c8" "L3 12e0"; do
  set -- $t
  FF_POKE="ff806e=$2,ff8070=$2" run ff_gameplay gp$1 6
done
