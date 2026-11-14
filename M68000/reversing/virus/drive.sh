#!/bin/bash
# Cold boot -> F1 (Virus) -> Union trainer menu (N x5 = no cheats) -> Return -> title -> SPACE -> SPACE -> wave-1 game on the
# launch pad.  Writes g_trainer, g_title, g_press, g_game1, g_game2 (.snap and .png) to $W/drive.  About 25 s.
# Usage: bash reversing/virus/drive.sh      (needs scratchpad/virus/aha.st: README "Provenance")
cd "$(dirname "$0")/../.." || exit 1
W=${VIRUS_WORK:-scratchpad/virus}; O=$W/drive; mkdir -p $O
{
 echo "s 20000000"            # AUTO\MULTI2.PRG menu is up, waiting in GEMDOS Crawcin
 echo "kbd 3b"; echo "s 60000"; echo "kbd bb"      # F1 = VIRUS (loads BR.TOS -> VIRUS.TEX, the Union trainer menu)
 echo "s 38000000"            # Union intro and fade until the trainer menu takes keys
 echo "snap $O/g_trainer.snap"
 echo "s 3000000"
 for i in 1 2 3 4 5; do echo "kbd 31"; echo "s 60000"; echo "kbd b1"; echo "s 1500000"; done   # N x5: energy, lives, rockets (extras ignored)
 echo "s 3000000"
 echo "kbd 1c"; echo "s 60000"; echo "kbd 9c"; echo "s 1000000"     # Return
 echo "snap $O/g_title.snap"
 echo "kbd 39"; echo "s 60000"; echo "kbd b9"; echo "s 10000000"    # SPACE on the title picture -> "Press R to redefine..." page
 echo "snap $O/g_press.snap"
 echo "kbd 39"; echo "s 60000"; echo "kbd b9"; echo "s 6000000"     # SPACE again -> the game on the pad (wave 1)
 echo "snap $O/g_game1.snap"
 echo "s 3000000"; echo "snap $O/g_game2.snap"
 echo q
} | ATARI_NOTRACE=1 dotnet exec bin/Debug/net8.0/M68000.dll --disk-a $W/aha.st 100 repl 2>&1 | grep -E "REPL|rror|saved"
for n in g_trainer g_title g_press g_game1 g_game2; do uv run python tools/snap_render.py $O/$n.snap $O/$n.png; done
