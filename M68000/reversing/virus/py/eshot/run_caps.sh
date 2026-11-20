#!/bin/bash
# Captures for the enemy-shot gate: natural play from the pursuer corpus snapshots (waves 1 to 4). One emulator at a time.
d="$(cd "$(dirname "$0")" && pwd)"; r="$d"; while [ ! -f "$r/tools/rdis.py" ]; do r="$(dirname "$r")"; done
cd "$r" || exit 1
W="${VIRUS_WORK:-scratchpad/virus}/eshot"; export VIRUS_MPC_WORK="$PWD/$W/mpcwork"; mkdir -p "$W/caps" "$VIRUS_MPC_WORK"
SN="${VIRUS_SNAPS:-scratchpad/virus/pursuer/snaps}"; SN2=scratchpad/virus/behaviours/gate/snaps    # game 050's p135..p495
for s in ${CAPS:-g014_500 g045_500 g093_400 g014_200 g093_200 p415 p495 g014_100 g045_100 p255 g093_600 g045_700 p135 g045_400 g093_300 g014_300}; do
  f="$SN/$s.snap"; [ -f "$f" ] || f="$SN2/$s.snap"
  [ "${SKIP_DONE:-0}" = 1 ] && [ -s "$W/caps/$s.json" ] && continue
  uv run python "$d/cap_eshot.py" "$f" 2500 "$W/caps/$s.json" | tail -1
done
