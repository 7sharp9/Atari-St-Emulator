#!/bin/bash
# Gate: Virus's demo flight run on Hatari from this emulator's state (demo/S1b.snap), interrupts live, compared with
# this emulator at every Ship_Tick ($255c2) arrival (hatari_game.py), then the control (one pool byte poked for Hatari
# must make arrival 0 differ).  Default: 2,000 ticks, about 90 s.  `full`: the whole flight to its game over ($25bc0),
# 11,782 ticks, about 6 minutes and 210 MB of logs.
# Needs scratchpad/virus/demo/S1b.snap (bash reversing/virus/py/demo/capture.sh) and a Hatari binary (HATARI).
# Output: scratchpad/learning/hatari_game/gate.log, and flight1/ or t2000/ and control/.
cd "$(dirname "$0")/../../.." || exit 1
P=reversing/learning/py/hatari_game.py; S=${VIRUS_WORK:-scratchpad/virus}/demo/S1b.snap
O=scratchpad/learning/hatari_game; mkdir -p $O; rm -f $O/gate.log
if [ "$1" = full ]; then python3 $P $S 255c2 40000 $O/flight1 --until 25bc0 > $O/one.txt 2>&1; rc=$?
else python3 $P $S 255c2 2000 $O/t2000 > $O/one.txt 2>&1; rc=$?; fi
grep -v '^WARNING\|^---' $O/one.txt | tee -a $O/gate.log; echo "run rc=$rc" | tee -a $O/gate.log
python3 $P $S 255c2 20 $O/control --control > $O/ctl.txt 2>&1; crc=$?
echo "control (pool byte \$31d57 poked for Hatari): rc=$crc, $(grep 'arrivals equal' $O/ctl.txt)" | tee -a $O/gate.log
[ $rc = 0 ] && [ $crc = 1 ] && grep -q 'arrivals equal on every range: 0/20' $O/ctl.txt
