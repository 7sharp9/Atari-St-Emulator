#!/bin/bash
# The player's shot, the wave-0 actors and the ship-hit box (shot.py) against four fresh captures of demo flight 1
# (demo/S1b.snap: autopilot, fire forced, aim wobbled with fire forced, fire cleared), each gate with its controls.
# Captures go to scratchpad/virus/mpc/gate/ (VIRUS_MPC_WORK overrides).
d="$(cd "$(dirname "$0")" && pwd)"; r="$d"; while [ ! -f "$r/tools/rdis.py" ]; do r="$(dirname "$r")"; done
cd "$r" || exit 1
W="${VIRUS_MPC_WORK:-$r/scratchpad/virus/mpc/gate}"; mkdir -p "$W"
uv run python "$d/shot_capture.py" auto 1190 "$W/cap_auto.json" || exit 1
uv run python "$d/shot_capture.py" autofire 1190 "$W/cap_autofire.json" || exit 1
uv run python "$d/shot_capture.py" wobble 1050 "$W/cap_wobble.json" || exit 1
uv run python "$d/shot_capture.py" nofire 1500 "$W/cap_nofire.json" || exit 1
C="$W/cap_auto.json $W/cap_autofire.json $W/cap_wobble.json $W/cap_nofire.json"
echo "== gate_shot"; uv run python "$d/gate_shot.py" $C || exit 1
echo "== gate_actor"; uv run python "$d/gate_actor.py" $C || exit 1
echo "== gate_danger"; uv run python "$d/gate_danger.py" || exit 1
echo "== control gate_danger"; uv run python "$d/gate_danger.py" --control
for c in shift grav box80; do echo "== control gate_shot $c"; uv run python "$d/gate_shot.py" $C --control $c | grep -E "^  (spawn_rec|flight|hit|nohit) "; done
echo "== control gate_actor spring"; uv run python "$d/gate_actor.py" $C --control spring | grep -E "^  seeder/fly "
