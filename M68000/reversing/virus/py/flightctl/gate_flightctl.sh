#!/bin/bash
# Gate flightctl: the mouse routine $254aa as a model, the ship matrix $270d4 and its writers, the pad path and ceiling cut,
# and which exit of the tick ends each life in two chain games.  Fresh captures into $W/flightctl/gate/.  About 9 minutes.
# Inputs: $W/fl/f1.snap, f4.snap, $W/drive/g_game2.snap, $W/demo/S1b.snap, $W/chain/long100/starts/main_g001.snap and main_g003.snap.
# One poke, labelled: pad_ceiling.py pokes the fuel word $32a2e to $0100 in one of its pad runs (its unpoked run is the control).
d="$(cd "$(dirname "$0")" && pwd)"; r="$d"; while [ ! -f "$r/tools/rdis.py" ]; do r="$(dirname "$r")"; done
cd "$r" || exit 1
W=${VIRUS_WORK:-scratchpad/virus}; O=$W/flightctl/gate; mkdir -p "$O"
F="$W/fl/f1.snap"; S="$W/demo/S1b.snap"; C="$W/chain/long100/starts"
ck() { if grep -q 'REPL error' "$1"; then echo "REPL error in $1"; exit 1; fi; }
echo "== 1. mouse routine \$254aa (live game f1.snap, 300 x mouse move, seed 7)"
python3 "$d/mouse_model.py" run "$F" 300 7 "$O/mouse_f1.txt" || exit 1; ck "$O/mouse_f1.txt"
python3 "$d/mouse_model.py" check "$F" "$O/mouse_f1.txt" || exit 1
python3 "$d/mouse_model.py" acc 300 7 "$O/mouse_f1.txt" || exit 1
echo "== 2. ship matrix \$270d4 (demo S1b.snap, 120 ticks)"
python3 "$d/matrix_writers.py" tick "$S" 120 "$O/mw_tick.txt" || exit 1; ck "$O/mw_tick.txt"
python3 "$d/matrix_writers.py" tickcheck "$O/mw_tick.txt" "$S" || exit 1
python3 "$d/matrix_writers.py" capture "$S" 120 "$O/mw_cap.txt" || exit 1; ck "$O/mw_cap.txt"
python3 "$d/matrix_writers.py" analyse "$O/mw_cap.txt" "$S" || exit 1
echo "== 3. pad path, refuel, thrust, ceiling cut"
python3 "$d/pad_ceiling.py" || exit 1
echo "== 4. which exit ends each life (unpoked attract games; budgets cover game 1's six losses and game 3's first four)"
python3 "$d/death_census.py" "$C/main_g001.snap" 600000000 "$O/census_g001.txt" || exit 1
python3 "$d/death_census.py" "$C/main_g003.snap" 640000000 "$O/census_g003.txt" || exit 1
echo flightctl gate done
