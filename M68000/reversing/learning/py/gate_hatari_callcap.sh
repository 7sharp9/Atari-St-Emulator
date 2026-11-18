#!/bin/bash
# Gate: eight Virus routines, three calls each, run on Hatari's CPU from this emulator's state and compared with this
# emulator's callcap (hatari_callcap.py), then the control (one flipped RAM byte must be the one byte reported).
# Needs scratchpad/virus/demo/S1b.snap (bash reversing/virus/py/demo/capture.sh) and a Hatari binary (HATARI).
# Output: scratchpad/learning/hatari_callcap/gate.log and one directory per call.  About 90 s.
cd "$(dirname "$0")/../../.." || exit 1
P=reversing/learning/py/hatari_callcap.py; S=${VIRUS_WORK:-scratchpad/virus}/demo/S1b.snap
O=scratchpad/learning/hatari_callcap; mkdir -p $O; rm -f $O/gate.log
ok=0; n=0
# Ship_Tick, Pool_UpdateAll, ObjectPool_UpdateAll, Landscape_HeightAt, Input_Autopilot, Landscape_BuildGridAndDraw,
# Attitude_BuildMatrix, Target_FindNearest
# Target_FindNearest runs under 150 times in the 50M-step budget from S1b, so its third sample is call 60.
for a in 255c2 2157c 1fa72 24754 2538c 24098 1f646 2529a; do for k in 1 37 150; do
  [ $a = 2529a ] && [ $k = 150 ] && k=60
  n=$((n+1)); python3 $P $S $a $k > $O/one.txt 2>&1; rc=$?
  tr '\n' ' ' < $O/one.txt | tee -a $O/gate.log; echo " rc=$rc" | tee -a $O/gate.log
  [ $rc = 0 ] && ok=$((ok+1))
done; done
echo "Hatari == callcap (RAM \$8-\$fffff and 16 registers): $ok/$n calls" | tee -a $O/gate.log
python3 $P $S 255c2 37 --control > $O/one.txt 2>&1; rc=$?
echo "control (byte \$7fff0 flipped for Hatari): rc=$rc, $(sed -n 2p $O/one.txt)" | tee -a $O/gate.log
[ $ok = $n ] && [ $rc = 1 ] && grep -q '1048563/1048564' $O/one.txt
