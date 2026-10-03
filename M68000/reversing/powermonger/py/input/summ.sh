#!/bin/sh
# summarise segment outputs: nonzero hits + final state lines
for f in "$1"/out_*.txt; do
  echo "--- $(basename $f)"
  awk '/^  \$/ && $2>0 {printf "%s=%s ", $1,$2} END{print ""}' "$f"
  grep -v '^  \$' "$f" | grep -E '^[0-9a-f][0-9a-f] ' | tail -7 | tr '\n' '|'; echo
done
