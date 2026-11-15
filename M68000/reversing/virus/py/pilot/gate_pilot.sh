#!/bin/bash
# Gate: the pilot-tick model (py/pilot/pilot_model.py) against callcap $2538c over 3,500 pilot calls of demo flight 1, from a
# FRESH capture (about 70 s), each result followed by its broken-model controls.  Needs scratchpad/virus/demo/S1b.snap
# (bash reversing/virus/py/demo/capture.sh).  Data: $W/pilot/.   Second argument "census": the scan census instead (about 150 s).
cd "$(dirname "$0")/../../../.." || exit 1
W=${VIRUS_WORK:-scratchpad/virus}; O=$W/pilot; P=reversing/virus/py/pilot; mkdir -p $O
if [ "$1" = census ]; then
  rm -f $O/census.log $O/census.end.snap
  echo "== census of the nearest-record scan (bp \$253a4, 1600 stops from S1b, unpoked)"
  uv run python $P/census_scan.py 1600 $O/census.log $W/demo/S1b.snap || exit 1
  uv run python $P/census_report.py $O/census.log
  exit 0
fi
rm -f $O/ticks.log $O/ticks.end.snap
echo "== capture: bp \$2538c + callcap \$2538c, 3500 stops from S1b"
uv run python $P/capture_pilot.py 3500 $O/ticks.log $W/demo/S1b.snap || exit 1
echo "== model"
uv run python $P/pilot_model.py $O/ticks.log $W/demo/S1b.snap
for c in scan_lt thrust_cap turn_step no_asr fire_range; do
  echo "-- control $c (must fail)"; uv run python $P/pilot_model.py $O/ticks.log $W/demo/S1b.snap --control $c | sed -n 2p
done
