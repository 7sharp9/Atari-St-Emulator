#!/bin/bash
# Fresh demo-experiment snapshots for the Virus demo gates (reversing/virus/demo.md), written to $W/demo (W defaults to
# scratchpad/virus).  Needs $W/drive/g_press.snap and g_title.snap (bash reversing/virus/drive.sh) and $W/aha.st.
# About 6 minutes, one emulator at a time.  Poked: the power-up RNG seed ($2706e/$27072) at a scatter stop in the "seed"
# snapshots; nothing else.  Output snapshots:
#   S1b          flight 1: game start ($230c0, demo flag $62a5f = $ff) reached from g_title with no input
#   fl/Q1,Q2,Q3  first scatter call ($236f8) after an ESC out of the previous flight: scatter A (jsr $2336a at $25be8, stack word $5bee)
#   fl/S2,S3,S4  the next flights started naturally;  fl/Sp2,Sp3,Sp4  the same with the RNG seed poked at Q*
#   c1/Q         the scatter call after A: scatter B (jsr $2336a at $230a6, stack word $30ac); the ESC hold of 400,000 steps lets A run first
#   ctl/H,Q,S    a human game idled 20M steps, ESC (A runs inside the 400,000-step hold), stop at scatter B, seed poked, next demo
cd "$(dirname "$0")/../../../.." || exit 1
W=${VIRUS_WORK:-scratchpad/virus}; O=$W/demo; mkdir -p $O/fl $O/c1 $O/ctl
R() { ATARI_NOTRACE=1 dotnet exec bin/Debug/net8.0/M68000.dll resume "$1" repl 2>&1; }
chk() { if grep -q "REPL error" "$1"; then echo "REPL error in $1"; exit 1; fi; }
SEED='echo "w 2706e 1234abdf"; echo "w 27072 5678e7f2"'
ESC='echo "s 3000000"; echo "kbd 01"; echo "s 400000"; echo "kbd 81"'
# 1. flight 1
{ echo "bp 20e74 300000000"; echo "snap $O/P1.snap"; echo "bp 230c0 100000000"; echo "m 62a5f 1"; echo "snap $O/S1b.snap"; echo q; } | R $W/drive/g_title.snap > $O/s1b.log; chk $O/s1b.log
# 2. flights 2..4 by ESC (restart path $25be8), natural and seed-poked
uv run python reversing/virus/py/demo/flights.py $O/S1b.snap $O/fl 3 20000000 > $O/flights.txt
# 3. chain 1: a g_press-lineage demo, ESC, first scatter call (restart path $230a6)
{ echo "bp 230c0 60000000"; echo "snap $O/c1/S1.snap"; eval "$ESC"; echo "bp 20e74 120000000"; echo "bp 236f8 150000000"; echo "m 2706e 8"; echo "m 6fffe 2"; echo "snap $O/c1/Q.snap"; echo q; } | R $W/drive/g_press.snap > $O/c1.log; chk $O/c1.log
# 4. a human game (SPACE on the press page), idled 20M steps, ESC, scatter stop, seed poke, next demo
{ echo "kbd 39"; echo "s 60000"; echo "kbd b9"; echo "bp 230c0 60000000"; echo "m 62a5f 1"; echo "snap $O/ctl/H.snap"; echo q; } | R $W/drive/g_press.snap > $O/h.log; chk $O/h.log
{ echo "s 20000000"; eval "$ESC"; echo "bp 236f8 150000000"; echo "m 6fffe 2"; echo "snap $O/ctl/Q.snap"; eval "$SEED"; echo "bp 230c0 150000000"; echo "m 62a5f 1"; echo "snap $O/ctl/S.snap"; echo q; } | R $O/ctl/H.snap > $O/ctl.log; chk $O/ctl.log
echo captured
