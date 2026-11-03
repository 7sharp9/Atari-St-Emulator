#!/bin/bash
# snapdiff_proof.sh: the semantic snapshot diff on Cadaver's joystick A/B (DEVELOPING.md "Memory layouts and the
# semantic snapshot diff"). From s96/r6/s3_flask.snap: `kbd ff 08` (right) then `s 300000`, and a same-budget
# no-input control; tools/snapdiff.py against the start for each. Expected: the input diff names
# objects[0:hero].x_lead 29 -> 41 (and x_trail 23 -> 35); the control names no hero field.
#   bash reversing/cadaver/py/snapdiff_proof.sh            # from M68000/
# DATA (default: this checkout's M68000) holds the snapshot, the disk's parent dir and bin/'s DLL; a worktree points
# it at the main checkout. Output: <this checkout>/scratchpad/layout/cadaver/.
set -e
HERE=$(cd "$(dirname "$0")/../../.." && pwd)
DATA=${DATA:-$HERE}
O=$HERE/scratchpad/layout/cadaver
mkdir -p "$O"
cp "$DATA/scratchpad/cadaver/s96/r6/s3_flask.snap" "$O/start.snap"
DISK="$DATA/../Cadaver/Cadaver (1990)(Image Works)[cr Empire][one disk].st"
printf 'kbd ff 08\ns 300000\nsnap %s\nq\n' "$O/input.snap" > "$O/input.repl"
printf 's 300000\nsnap %s\nq\n' "$O/control.snap" > "$O/control.repl"
cd "$DATA"
for k in input control; do
  rm -f "$O/$k.snap"
  ATARI_NOTRACE=1 dotnet exec "$DATA/bin/Debug/net8.0/M68000.dll" resume "$O/start.snap" repl --disk-a "$DISK" \
    < "$O/$k.repl" > "$O/$k.log" 2>&1
  test -s "$O/$k.snap" || { echo "no $k.snap; log:"; cat "$O/$k.log"; exit 1; }
done
cd "$HERE"
for k in input control; do
  echo "######## $k"
  uv run python tools/snapdiff.py reversing/cadaver/layout.toml "$O/start.snap" "$O/$k.snap" --regs | tee "$O/diff_$k.txt"
done
