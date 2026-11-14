#!/bin/bash
# Natural game over for the Virus demo gates (reversing/virus/demo.md, "Natural death and game over").  Needs capture.sh's
# $W/demo/S1b.snap.  About 6 minutes.  The demo flies from S1b with no input until its last life is lost on its own (fuel runs
# out, the ship falls and the game's collision kills it), then runs the game-over sequence unaided.  Poked: the power-up RNG seed
# at scatter B (jsr $2336a at $230a6) in N1/E1, and in N1z four stale bytes zeroed ($27139, $2713a, $27144, $27147).
# Writes $W/demo/death/: long7.snap (stopped at the life decrement $25ba0 with lives = 1), nB.snap (stopped at scatter B after the
# unaided game over), N1.snap (next demo start, seed poked at B), E1.snap (the same after an ESC instead of a death), N1z.snap.
cd "$(dirname "$0")/../../../.." || exit 1
W=${VIRUS_WORK:-scratchpad/virus}; O=$W/demo/death; mkdir -p $O
R() { ATARI_NOTRACE=1 dotnet exec bin/Debug/net8.0/M68000.dll resume "$1" repl 2>&1; }
SEEDP='echo "w 2706e 1234abdf"; echo "w 27072 5678e7f2"'
# seven stops on $25ba0 in 200M-step chunks (chunks 1 and 8 end at the cap without a death in this demo; chunk 7 is the last life)
{ for i in 1 2 3 4 5 6 7; do echo "bp 25ba0 200000000"; echo "m 32a54 2"; done; echo "snap $O/long7.snap"; echo q; } | R $W/demo/S1b.snap > $O/long.log
{ echo "m 32a54 2"; echo "bp 236f8 50000000"; echo "m 6fffe 2"; echo "bp 230a6 400000000"; echo "snap $O/nB.snap"; eval "$SEEDP"; echo "bp 230c0 150000000"; echo "m 62a5f 1"; echo "snap $O/N1.snap"; echo q; } | R $O/long7.snap > $O/n1.log
{ echo "s 3000000"; echo "kbd 01"; echo "s 400000"; echo "kbd 81"; echo "bp 230a6 400000000"; eval "$SEEDP"; echo "bp 230c0 150000000"; echo "m 62a5f 1"; echo "snap $O/E1.snap"; echo q; } | R $W/demo/S1b.snap > $O/e1.log
{ echo "wb 27139 00"; echo "wb 2713a 00"; echo "wb 27144 00"; echo "wb 27147 00"; echo "snap $O/N1z.snap"; echo q; } | R $O/N1.snap > $O/n1z.log
for f in long n1 e1 n1z; do if grep -q "REPL error" $O/$f.log; then echo "REPL error in $O/$f.log"; exit 1; fi; done
echo captured
