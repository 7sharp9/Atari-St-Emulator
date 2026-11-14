#!/bin/bash
# Gate for README "Hidden keys and leftovers": the $118e meter proof with its broken control, the title view 33 and its
# keypad viewer, the forced $3dbc and $1e462 calls (leftovers.py).
here=$(cd "$(dirname "$0")" && pwd)
root=$here; while [ ! -f "$root/tools/rdis.py" ]; do root=$(dirname "$root"); done
py="uv run --project $root python -I"
cd "$root"
for m in "meter" "meter --break" title spawn; do $py "$here/leftovers.py" $m | grep -E '^(meter|title|forced)'; done
