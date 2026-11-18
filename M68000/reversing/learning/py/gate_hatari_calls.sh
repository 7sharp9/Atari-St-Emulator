#!/bin/bash
# Gate: every call of Virus's pilot corpus (Input_Autopilot $2538c, 3,496 natural entries of demo flight 1) checked on
# Hatari inside one flight (hatari_calls.py) against this emulator's callcap of the same entry, from a FRESH capture
# (reversing/virus/py/pilot/capture_pilot.py, about 70 s), then the control (the countdown byte $62a60 changed by
# Hatari at the first entry must make call 0 differ).  About 3 minutes.
# Needs scratchpad/virus/demo/S1b.snap (bash reversing/virus/py/demo/capture.sh) and a Hatari binary (HATARI).
# Output: scratchpad/learning/hatari_calls/gate.log, ticks.log, run/ and control/.
cd "$(dirname "$0")/../../.." || exit 1
P=reversing/learning/py/hatari_calls.py; S=${VIRUS_WORK:-scratchpad/virus}/demo/S1b.snap
O=scratchpad/learning/hatari_calls; mkdir -p $O; rm -f $O/gate.log $O/ticks.log $O/ticks.end.snap
uv run python reversing/virus/py/pilot/capture_pilot.py 3500 $O/ticks.log $S | tee -a $O/gate.log || exit 1
python3 $P $S $O/ticks.log $O/run > $O/one.txt 2>&1; rc=$?
cat $O/one.txt | tee -a $O/gate.log; echo "run rc=$rc" | tee -a $O/gate.log
python3 $P $S $O/ticks.log $O/control --calls 20 --control > $O/ctl.txt 2>&1; crc=$?
echo "control (countdown \$62a60 changed by Hatari at the first entry): rc=$crc, $(grep 'equal at entry' $O/ctl.txt); $(grep 'first difference' $O/ctl.txt)" | tee -a $O/gate.log
[ $rc = 0 ] && [ $crc = 1 ] && grep -q 'first difference at call 0' $O/ctl.txt && grep -q 'equal at return.*: 3496/3496' $O/one.txt
