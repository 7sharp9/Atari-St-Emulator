#!/usr/bin/env bash
# run from M68000/. order_run.sh <name> <steps-after> <clicks.py tokens...>
# Resumes mission 1 settled (scratchpad/pm123/win/m1_s0.snap, rebuilt by drive_win.sh), plays the
# clicks, runs <steps-after>, snapshots, and prints the lords (sides.py) and the selected group
# (group.py). Output in $PM_WORK/orders/<name> (default scratchpad/pmwork). Pass each REPL poke as
# its own token (w:addr:long): zsh does not split an unquoted variable. Strategy.md "What each order
# does" lists the runs.
n=$1; st=$2; shift 2; d=${PM_WORK:-scratchpad/pmwork}/orders/$n; mkdir -p $d; P=reversing/powermonger/py
python3 $P/clicks.py "$@" s:$st snap:$d/end.snap q > $d/cmds
ATARI_NOTRACE=1 dotnet exec bin/Debug/net8.0/M68000.dll resume ${SNAP:-scratchpad/pm123/win/m1_s0.snap} repl --disk-a scratchpad/powermonger.st < $d/cmds > $d/out.txt 2>&1
python3 $P/snap2ram.py $d/end.snap >/dev/null
python3 $P/sides.py $d/end.ram | sed -n 3,5p
python3 $P/group.py $d/end.ram
grep -A12 'hits over' $d/out.txt | grep '\$' || true
