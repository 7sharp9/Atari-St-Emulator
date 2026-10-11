#!/bin/bash
# Run one of this directory's REPL scripts with its snapshot/output paths moved to $PM_WORK.
# Usage: run_repl.sh <name> [start-snap]
#   name        boxclick | badge | rclick | xfer | icons   start pm142/rand1.snap (default)
#               xfer3 (start rand1; stops at $1c18, writes xfer_pre.snap), then xfer4 (start $PM_WORK/xfer_pre.snap)
#               arrive | fly                               start $PM_WORK/run_ord.snap (from drive_order.sh)
# The .repl files name scratchpad/pm150/captain2; that string is replaced by $PM_WORK.
# Output: $PM_WORK/<name>.out
set -e
d="$(cd "$(dirname "$0")" && pwd)"; here="$d"
while [ ! -f "$d/tools/rdis.py" ] && [ "$d" != / ]; do d=$(dirname "$d"); done
[ -f "$d/tools/rdis.py" ] || d="$M68000_ROOT"
cd "$d"
W="${PM_WORK:-scratchpad/pm150/captain2}"; mkdir -p "$W"
name="$1"; snap="${2:-scratchpad/pm142/rand1.snap}"
sed "s#scratchpad/pm150/captain2#$W#g" "$here/$name.repl" > "$W/$name.run.repl"
ATARI_NOTRACE=1 dotnet exec bin/Debug/net8.0/M68000.dll resume "$snap" repl < "$W/$name.run.repl" > "$W/$name.out" 2>&1
echo "done: $W/$name.out"
