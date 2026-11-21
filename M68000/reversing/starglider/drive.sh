#!/bin/bash
# Cold boot -> Zuul boot-sector banner (SPACE, read by Bconin) -> Zuul menu (F2, polled from the ACIA at $b01e)
# -> 2.PRG -> STARGLID.PRG crack intro (SPACE, polled at $ae84) -> STAR.BIN title -> SPACE -> launched, in flight.
# Writes g_menu, g_intro, g_title, g_game1, g_game2 (.snap and .png) to $W/drive.
# Usage: bash reversing/starglider/drive.sh   (needs scratchpad/starglider/zuul208.st: README "Provenance")
cd "$(dirname "$0")/../.." || exit 1
W=${STARGLIDER_WORK:-scratchpad/starglider}; O=$W/drive; mkdir -p $O
{
 echo "s 300000000"                                       # boot-sector banner has printed and waits in Bconin
 echo "kbd 39"; echo "s 60000"; echo "kbd b9"
 echo "u b01e 400000000"; echo "s 2000000"                          # AUTO\LOADER.PRG menu polls $fffc02 for F1..F5
 echo "snap $O/g_menu.snap"
 echo "kbd 3c"; echo "s 2000000"; echo "kbd bc"           # F2 = Starglider (Pexec 2.PRG -> STARGLID.PRG)
 echo "u ae84 400000000"; echo "s 2000000"                          # crack intro polls $fffc02 for SPACE
 echo "snap $O/g_intro.snap"
 echo "kbd 39"; echo "s 2000000"; echo "kbd b9"           # Pexec STAR.BIN, title.tra, result.tra
 echo "s 20000000"
 echo "snap $O/g_title.snap"
 echo "kbd 39"; echo "s 200000"; echo "kbd b9"            # "Press SPACE BAR to launch"
 echo "s 40000000"
 echo "snap $O/g_game1.snap"
 echo "s 5000000"; echo "snap $O/g_game2.snap"
 echo q
} | ATARI_NOTRACE=1 dotnet exec bin/Debug/net8.0/M68000.dll --disk-a $W/zuul208.st 100 repl 2>&1 | grep -E "REPL|rror|saved|stopped|reached"
for n in g_menu g_intro g_title g_game1 g_game2; do uv run python tools/snap_render.py $O/$n.snap $O/$n.png; done
