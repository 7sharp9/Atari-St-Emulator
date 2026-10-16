#!/usr/bin/env bash
# The labelled-poke rendering checks: from pm88_f1.snap with the camera on (22,46)
# (10 men in view), poke one or more on-screen records at the $f898 frame driver,
# snap the state and the next $f898 frame, and score the port against the game.
# The neighbours of every `w` come from the no-poke control's state (ctl_0.ram):
# the run is deterministic up to the poke point (cmp of the _0 RAMs below).
#   run_cases.sh            (from anywhere; repo root found via tools/rdis.py)
# Output in ${PM_WORK:-scratchpad/pm156}/overlay/cap.
set -eu
d=$(cd "$(dirname "$0")" && pwd); here=$d
while [ ! -f "$d/tools/rdis.py" ]; do d=$(dirname "$d"); done
cd "$d"
C=${PM_WORK:-scratchpad/pm156}/overlay/cap
PY="uv run python"
[ -f "$C/ctl_0.ram" ] || "$here/poke_capture.sh" ctl 22 46 --
# case: name, then addr=hexbytes pokes
cases=(
  "plough 51beb=08 51c1d=08"
  "siege0e 51cbe=0e 51bc4=0e 51d86=0e 51bf6=0e"
  "siege0f 51cbe=0f 51bc4=0f 51d86=0f 51bf6=0f"
  "siege10 51cbe=10 51bc4=10 51d86=10 51bf6=10"
  "siege11 51cbe=11 51bc4=11 51d86=11 51bf6=11"
  "b6_28 51c98=1c 51b9e=1c 51b9d=00"
  "b6_28neg 51b9d=fe 51b9e=1c 51d5f=fe 51d60=1c"
  "b6_18 51c98=12 51b9e=12 51ba6=ffec"
  "b6_34 51c98=22 51b9e=22"
  "b6_36 51c98=24"
  "b6_38 51c98=26"
  "b6_42 51c98=2a"
  "plough_b7 51cb3=08 51bb9=08"
  "msiege0e 51cbe=0e 51cb1=32 51bc4=0e 51bb7=34"
  "msiege10 51cbe=10 51cb1=32 51bc4=10 51bb7=34"
  "melee 51cb1=32 51bb7=34"
  "siege84 51cbe=84 51bc4=84 51d86=84 51bf6=84"
  "msiege84 51cbe=84 51cb1=32 51bc4=84 51bb7=34"
  "msiege92 51cbe=92 51cb1=32 51bc4=92 51bb7=34"
)
only=${ONLY:-}
for c in "${cases[@]}"; do
  set -- $c; name=$1; shift
  [ -n "$only" ] && case " $only " in *" $name "*) ;; *) continue;; esac
  ws=(); while IFS= read -r l; do case $l in w*) ws+=("$l");; esac; done < <($PY "$here/pokew.py" "$C/ctl_0.ram" "$@")
  $PY "$here/pokew.py" "$C/ctl_0.ram" "$@" | grep '^#' | sed "s/^/$name /"
  "$here/poke_capture.sh" "$name" 22 46 -- "${ws[@]}"
done
