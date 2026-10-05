#!/bin/sh
# all.sh : regenerate every log from a cold boot and run both gate scripts (about 25 minutes with three MAME processes at once). Output: $FFD_BASE/out (default scratchpad/finalfight/twoplayer/out).
d=$(cd "$(dirname "$0")/.." && pwd); . "$d/run/env.sh"
mkdir -p "$runroot"
sh "$d/run/make_states.sh" ""
for r in run_p; do mkdir -p $base/$r/sta/ffightuc; cp $runroot/sta/ffightuc/*.sta $base/$r/sta/ffightuc/; done
( for c in 0 1 2; do sh "$d/py/char/run_chars.sh" $c; done; python3 "$d/py/char/gates.py" > "$out/gates_char.txt" 2>&1 ) &
( FFD_RUN=$base/run_p sh "$d/py/pvp/run_pvp.sh" ) &
sh "$d/py/pvp/run_long.sh"
wait
python3 "$d/py/pvp/gates.py" > "$out/gates_pvp.txt" 2>&1
tail -n 1 "$out/gates_char.txt" "$out/gates_pvp.txt"
