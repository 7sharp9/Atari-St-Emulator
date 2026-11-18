#!/bin/bash
# Gate: Virus's first demo flight from a cold boot of the disk in Hatari (hatari_boot.py: the crack's menus driven over
# the control socket), compared with this emulator's flight at every Ship_Tick ($255c2) arrival, then the control (one
# pool byte changed by Hatari at the game start must make arrival 0 differ).  Default: 2,000 ticks, about 2 minutes.
# `full`: the whole flight, 11,782 ticks, about 5 minutes and 150 MB of log.
# Needs this emulator's side from gate_hatari_game.sh (t2000/ours.json, or flight1/ours.json for `full`),
# scratchpad/virus/aha.st, scratchpad/virus/demo/S1b.snap and a Hatari binary (HATARI).
# Output: scratchpad/learning/hatari_boot/gate.log, and flight1/ or t2000/ and control/.
cd "$(dirname "$0")/../../.." || exit 1
P=reversing/learning/py/hatari_boot.py; S=${VIRUS_WORK:-scratchpad/virus}/demo/S1b.snap
G=scratchpad/learning/hatari_game; O=scratchpad/learning/hatari_boot; mkdir -p $O; rm -f $O/gate.log
if [ "$1" = full ]; then D=flight1; else D=t2000; fi
[ -f $G/$D/ours.json ] || { echo "missing $G/$D/ours.json: run gate_hatari_game.sh $1 first"; exit 1; }
python3 $P $G/$D/ours.json $O/$D --snap $S > $O/one.txt 2>&1; rc=$?
cat $O/one.txt | tee -a $O/gate.log; echo "run rc=$rc" | tee -a $O/gate.log
python3 $P $G/$D/ours.json $O/control --ticks 20 --control > $O/ctl.txt 2>&1; crc=$?
echo "control (pool byte \$31d57 changed by Hatari at the game start): rc=$crc, $(grep 'arrivals equal' $O/ctl.txt)" | tee -a $O/gate.log
[ $rc = 0 ] && [ $crc = 1 ] && grep -q 'arrivals equal on every range: 0/20' $O/ctl.txt
