#!/bin/sh
# level_poke.sh <N> <name> [frames] [stop]: POKED state.  Plan playright (coin, start, hold right, tap button 1), stage 1 starts about frame 840.
# At frame 900 poke $80046 = N-1 and set bit 4 of $80040 (the level-complete flag, tested at $6f4): the game then takes its own
# next-level path ($71c: level+1, $172a the Power Cola interlude, $6ba level init).  The interlude loops at $183c while that
# flag stays set, so frame 1500 clears the bit again.  N is a poke, everything after it is the game's own code.
N=$1; name=$2; here=$(cd "$(dirname "$0")/.." && pwd)
prev=$(printf '%x' $((N-1)))
"$here/run.sh" "$name" "${PLAN:-$here/lua/playright.lua}" "${3:-900:3600:20}" "${4:-3600}" "900:80046:$prev,900:80040:10:1:o,1500:80040:10:1:c"
