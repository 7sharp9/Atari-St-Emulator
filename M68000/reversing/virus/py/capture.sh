#!/bin/bash
# Fresh captures for every Virus gate, from $W/drive/g_game2.snap (made by reversing/virus/drive.sh).
# Writes under $W (default scratchpad/virus): fl/ (flight snapshots and grid callcaps), cap/ (REPL logs, level and wave
# callcaps).  Every REPL run is checked for "REPL error"; one emulator at a time.  About 4 minutes.
# Poked: stub code at $90000 (callcap targets) and, for flight_auto_bp.txt only, "wb 62a5f ff".
cd "$(dirname "$0")/../../.." || exit 1
W=${VIRUS_WORK:-scratchpad/virus}; mkdir -p $W/fl $W/cap
DLL=bin/Debug/net8.0/M68000.dll; D="--disk-a $W/aha.st"
repl() { # repl <snap>  (commands on stdin) -> stdout+stderr
  ATARI_NOTRACE=1 dotnet exec $DLL resume "$1" repl $D 2>&1; }
chk() { if grep -q "REPL error" "$1"; then echo "REPL error in $1"; exit 1; fi; }
G=$W/drive/g_game2.snap
# 1. flight: hold the left button (thrust), then four snapshots 900,000 steps apart with the mouse nudged
{ echo "mouse down l"; echo "s 40000"; echo "s 1500000"; echo "snap $W/fl/m_fire.snap"; echo q; } | repl $G > $W/cap/fire.log; chk $W/cap/fire.log
{ echo "mouse move 0 -20"; for i in 1 2 3 4; do echo "s 900000"; echo "snap $W/fl/f$i.snap"; done; echo q; } | repl $W/fl/m_fire.snap > $W/cap/fl.log; chk $W/cap/fl.log
# 2. grid callcaps
for i in 1 2 3 4; do printf "callcap 24098 20000000 $W/fl/cc$i.json\nq\n" | repl $W/fl/f$i.snap > $W/cap/cc$i.log; chk $W/cap/cc$i.log; done
# 3. landscape builder callcaps from the pad snapshot: $2336a(1) and $2336a(2) through a stub (poke: code at $90000)
for L in 1 2; do printf "w 90000 700%s4eb9\nw 90004 0002336a\nw 90008 4e754e75\ncallcap 90000 30000000 $W/cap/cc_l$L.json\nq\n" $L | repl $G > $W/cap/cc_l$L.log; chk $W/cap/cc_l$L.log; done
# 4. REPL logs
{ echo "bp 26b78 3000000"; echo "m 27354 700"; echo "m 275c4 400"; for i in $(seq 1 140); do echo "bp 26b78 3000000"; echo "r"; done; echo q; } | repl $W/fl/f2.snap > $W/cap/tile_bp.txt; chk $W/cap/tile_bp.txt
FL='echo "bp 255d4 200000"; echo "r"; echo "m 270b0 12"; echo "m 32a32 4"; echo "m 32a3a 2"; echo "m 32a2e 2"; echo "m 270d4 18"; echo "m 254a8 1"'
{ echo "mouse move 15 -10"; echo "s 3000"; for i in $(seq 1 120); do eval "$FL"; done; echo q; } | repl $W/fl/f1.snap > $W/cap/flight_bp.txt; chk $W/cap/flight_bp.txt
{ echo "wb 62a5f ff"; for i in $(seq 1 120); do eval "$FL"; done; echo q; } | repl $W/fl/f1.snap > $W/cap/flight_auto_bp.txt; chk $W/cap/flight_auto_bp.txt
printf 'wb 62a5f ff\nhits 300000 2538c 254aa\nq\n' | repl $W/fl/f1.snap > $W/cap/auto_hits.txt; chk $W/cap/auto_hits.txt
{ for i in $(seq 1 150); do echo "bp 2157c 400000"; echo "m 32a3e 2"; echo "m 31d54 1280"; echo "m 32a3a 2"; done; echo q; } | repl $W/fl/f1.snap > $W/cap/part_bp.txt; chk $W/cap/part_bp.txt
# 5. $20e74(n): the wave-start routine called with n = 3, 4, 5, 9, 10 through a stub (poke: code at $90000)
for n in 3 4 5 9 10; do printf "w 90000 7%s4eb9\nw 90004 00020e74\nw 90008 4e754e75\ncallcap 90000 30000000 $W/cap/cc_n$n.json\nq\n" "$(printf '%03x' $n)" | repl $W/fl/f1.snap > $W/cap/cc_n$n.log; chk $W/cap/cc_n$n.log; done
echo captured
