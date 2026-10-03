#!/bin/bash
# $3e9e..$3ea8 computes the eye frame D1 = word[$2df92] & 3 for $1699e. Poke the cursor X cell at the
# call site and step the two instructions; expect D1 = 0,1,2,3 for X = $a0..$a3.
ROOT="${M68000_ROOT:-$(cd "$(dirname "$0")/../../../.." && pwd)}"; cd "$ROOT" || exit 1
for x in 00a0 00a1 00a2 00a3; do
  printf "bp 3e9e 3000000\nw 2df92 ${x}0078\ns 2\nr\nq\n" | ATARI_NOTRACE=1 dotnet exec bin/Debug/net8.0/M68000.dll resume scratchpad/pm142/rand1.snap repl 2>&1 | grep -E "^D0" | tail -1 | sed "s/^/pointerX=$x /"
done
