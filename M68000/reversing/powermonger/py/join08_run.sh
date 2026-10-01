#!/usr/bin/env bash
# join08_run.sh <name> <steps> [poke ...]   (run from M68000/; output under ${PM_WORK:-scratchpad/pmwork}/join08/<name>)
# Order $08 (get men) from the conquered mission-1 state scratchpad/pm123/win/m1_ready.snap (lord 0's town is side 1,
# 5 able side-1 men in its houses, troops_field 5): arm icon (275,162), click the town on the minimap (22,51), run to the
# lead's arrival ($15122), count hits over <steps> on the whole join path and dump lead / group / lord 0 / five recruits
# before and after.  Pokes are REPL `w` tokens with ':' for spaces, e.g. w:516fc:00020000 (posture 2) or
# w:4e51c:00070000 (lord 0 troops_field 7).  Stage reports: join08_report.py <dir>/hits.out.
set -e
n=$1; st=$2; shift 2
J=$(cd "$(dirname "$0")" && pwd); ROOT=$(cd "$J/../../.." && pwd); cd "$ROOT"
D=${PM_WORK:-scratchpad/pmwork}/join08/$n; mkdir -p "$D"
SNAP=${SNAP:-scratchpad/pm123/win/m1_ready.snap}
python3 "$J/join08_cmds.py" 22,51 "$D" "$@" > "$D/cmds"
ATARI_NOTRACE=1 dotnet exec bin/Debug/net8.0/M68000.dll resume "$SNAP" repl --disk-a scratchpad/powermonger.st < "$D/cmds" > "$D/out.txt" 2>&1
python3 "$J/join08_watch.py" hits "$st" "$D/after.snap" > "$D/hits.cmds"
ATARI_NOTRACE=1 dotnet exec bin/Debug/net8.0/M68000.dll resume "$D/clicked.snap" repl --disk-a scratchpad/powermonger.st < "$D/hits.cmds" > "$D/hits.out" 2>&1
grep -A16 'hits over' "$D/hits.out" | grep -E '\$'
python3 "$J/join08_report.py" "$D/hits.out" | cut -c1-600
