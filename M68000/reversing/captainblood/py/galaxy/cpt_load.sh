#!/bin/bash
# cpt_load.sh : the cockpit's load button ($d044, hit entry 2: pointer (60,36), left click) reads BLOOD.CPT and replaces the
# galaxy table. Starts from the bridge snapshot key1_30M.snap, goes to the cockpit by drive.py (click at 160,50), dumps the
# table, clicks the load button, dumps again (ATARI_TRACE_GEMDOS=1 shows Fopen/Fread/Fclose), then runs cpt_check.py.
# Output: scratchpad/captainblood/galaxy/cpt/{cockpit.snap,cpt_load.txt,cpt_load.snap}. Run from anywhere in the repo.
R=$(cd "$(dirname "$0")" && pwd); while [ ! -f "$R/tools/rdis.py" ] && [ "$R" != / ]; do R=$(dirname "$R"); done
cd "$R" || exit 1
W=scratchpad/captainblood; O=$W/galaxy/cpt; mkdir -p $O; rm -f $O/cockpit.snap $O/cpt_load.txt
uv run python -I reversing/captainblood/py/drive.py $W/key1_30M.snap $O/cockpit.snap 160 50 4000000 | tail -1
{ echo "m ba4e 512"; echo "mouse move -100 -14"; echo "s 130000"; echo "mouse down l"; echo "s 40000"; echo "mouse up l"
  echo "hits 3000000 d0ea"; echo "s 3000000"; echo "m ba4e 512"; echo "snap $O/cpt_load.snap"; } \
 | ATARI_NOTRACE=1 ATARI_TRACE_GEMDOS=1 dotnet exec bin/Debug/net8.0/M68000.dll resume $O/cockpit.snap repl > $O/cpt_load.txt 2>&1
grep "GEMDOS_CALL.*func=\$00\(3d\|3f\|3e\)\|d0ea" $O/cpt_load.txt
uv run python reversing/captainblood/py/galaxy/cpt_check.py $O/cpt_load.txt $W/depacked/BLOOD.CPT
