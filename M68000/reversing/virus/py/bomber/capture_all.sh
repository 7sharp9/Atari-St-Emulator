#!/bin/bash
# stamped natural captures for the bomber gates (about 40 s each); output under $VIRUS_WORK/bomber/caps
d="$(cd "$(dirname "$0")" && pwd)"; while [ ! -f "$d/tools/rdis.py" ]; do d="$(dirname "$d")"; [ "$d" = / ] && exit 9; done; cd "$d"
W="${VIRUS_WORK:-scratchpad/virus}"; if [ -n "$BOMBER_OUT" ]; then O="$BOMBER_OUT"; else O="$W/bomber/caps"; fi; mkdir -p "$O"
S="$W/pursuer/snaps"; P="$W/behaviours/gate/snaps"
H="$(cd "$(dirname "$0")" && pwd)"
for x in "$S/g014_100" "$S/g014_200" "$S/g014_500" "$S/g014_700" "$S/g045_300" "$S/g045_500" "$S/g093_400" "$S/g093_600" "$P/p255" "$P/p415"; do
  n=$(basename $x); uv run python "$H/cap_b.py" $x.snap ${TICKS:-2500} "$O/b_$n.json"
done
# wave starts: the pool right after `$20e74` built it (landscape/natural.sh); the bombers hatch 80 to 580 ticks later. The game needs
# more than 3M steps to reach its first flight tick from these (bp stops mid-build), hence BCAP_START.
for n in 0 1 2 3 4; do
  BCAP_START=60000000 uv run python "$H/cap_b.py" "$W/landscape/gate/natural/built_$n.snap" 800 "$O/b_built$n.json"
done
