#!/bin/bash
# runarms.sh < arms.txt : one arm per line "<name> <pre> <hold>"; POKE in the environment applies to every line.
# Prints each arm's breakpoint line. Then: uv run python reversing/captainblood/py/galaxy/diffarms.py
D=$(cd "$(dirname "$0")" && pwd); R=$D; while [ ! -f "$R/tools/rdis.py" ] && [ "$R" != / ]; do R=$(dirname "$R"); done
while read n pre hold; do
  "$D/arm.sh" $n $pre $hold
  echo $n $(grep -h "breakpoint" "$R/scratchpad/captainblood/galaxy/arms/$n.txt")
done
