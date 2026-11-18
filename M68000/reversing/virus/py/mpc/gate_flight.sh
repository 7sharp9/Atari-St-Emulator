#!/bin/bash
# The ship tick as a model (exact.py) against the game, through the replay harness (replay.py, stserver):
# the capture replayed with its controls, 21 seeded control sequences off the capture, a landing, empty fuel.
# Fresh replays into scratchpad/virus/mpc/gate/ (VIRUS_MPC_WORK overrides). About 4 minutes.
d="$(cd "$(dirname "$0")" && pwd)"; r="$d"; while [ ! -f "$r/tools/rdis.py" ]; do r="$(dirname "$r")"; done
cd "$r" || exit 1
for s in check_capture gen_controls check_model check_landing check_misc; do
  uv run python "$d/$s.py" || { echo "FAILED $s"; exit 1; }
done
