#!/bin/bash
# User-mode privilege and illegal-encoding probes for the 68000 core, which the SingleStepTests
# vectors cannot give (none of their cases starts in user mode).
#
#   bash tools/priv_check.sh [<M68000.dll>] [<outdir>]
#
# Makes a 30M-step diskless snapshot (TOS idle, supervisor), pokes `move #$0700,sr` (drop to user
# mode, interrupts masked) followed by one probe instruction at $70000, and runs both under
# `callcap $70000 2`. A privileged instruction must leave the PC at the vector-8 handler (the long
# at $20) and an unassigned encoding at the vector-4 handler (the long at $10). A build without
# the checks ends at $70006/$70008 (the instruction ran), at the popped PC for RTE, or THREW.
set -u
d=$(cd "$(dirname "$0")" && pwd)
while [ ! -f "$d/tools/rdis.py" ]; do d=$(dirname "$d"); [ "$d" = / ] && { echo "no repo root" >&2; exit 2; }; done
cd "$d"
DLL=${1:-bin/Debug/net8.0/M68000.dll}
R=${2:-scratchpad/priv_check}
mkdir -p "$R"
export ATARI_NOTRACE=1
rm -f "$R/boot30m.snap"
dotnet exec "$DLL" 30000000 snapshot "$R/boot30m.snap" >/dev/null 2>&1 || { echo "snapshot failed" >&2; exit 2; }
vec() { printf 'm %s 4\nq\n' "$1" | dotnet exec "$DLL" resume "$R/boot30m.snap" repl 2>/dev/null | grep -Eo '^([0-9a-f]{2} ){3}[0-9a-f]{2}' | head -1 | tr -d ' '; }
V8=$(vec 20); V4=$(vec 10)
[ -n "$V8" ] && [ -n "$V4" ] || { echo "could not read vectors" >&2; exit 2; }
pass=0; total=0
probe() { # name, 8 hex digits at $70004, expected PC
  total=$((total+1))
  out=$(printf 'w 70000 46fc0700\nw 70004 %s\nw 70008 4e714e71\ncallcap 70000 2\nq\n' "$2" \
        | dotnet exec "$DLL" resume "$R/boot30m.snap" repl 2>&1 | grep -- '--- callcap')
  pc=$(echo "$out" | grep -Eo 'PC=\$[0-9a-f]+' | head -1 | tr -d 'PC=$')
  want=$(printf '%x' $((16#$3)))
  if [ "$pc" = "$want" ]; then pass=$((pass+1)); echo "PASS $1: PC=\$$pc"; else echo "FAIL $1: wanted PC=\$$want, got: ${out:0:90}"; fi
}
probe "move #\$2700,sr" 46fc2700 "$V8"
probe "ori #\$2000,sr"  007c2000 "$V8"
probe "andi #\$ffff,sr" 027cffff "$V8"
probe "eori #\$2000,sr" 0a7c2000 "$V8"
probe "rte"             4e734e71 "$V8"
probe "move a0,usp"     4e604e71 "$V8"
probe "move usp,a0"     4e684e71 "$V8"
probe "reset"           4e704e71 "$V8"
probe "stop #\$2000"    4e722000 "$V8"
probe "\$42c0 (68010 move ccr,d0)" 42c04e71 "$V4"
probe "clr.w #imm (\$427c)"        427c0000 "$V4"
echo "priv_check: $pass/$total"
[ "$pass" = "$total" ]
