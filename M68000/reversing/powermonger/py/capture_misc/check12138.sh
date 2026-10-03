#!/bin/bash
# $12138 (check_sh, the sprite pick): six callcap cases from the first natural entry of pm142/rand1.snap.
# Expect: idle 0 bytes, armed_inside 33, armed_click 84, armed_outside 0, examine_click 368, examine_noclick 0.
ROOT="${M68000_ROOT:-$(cd "$(dirname "$0")/../../../.." && pwd)}"; cd "$ROOT" || exit 1
SNAP=scratchpad/pm142/rand1.snap
run() { # name pokes...
  name=$1; shift
  { echo "bp 12138 3000000"; for p in "$@"; do echo "w $p"; done; echo "callcap 12138 200000"; echo q; } \
    | ATARI_NOTRACE=1 dotnet exec bin/Debug/net8.0/M68000.dll resume $SNAP repl 2>&1 | grep -E "^--- callcap" | sed -E "s/^--- callcap [^:]*: returned, trace hash [^,]*, /[$name] /; s/, entrySP.*//"
}
run idle
run armed_inside   "2df92 00ce006a" "57fd4 00010000"
run armed_click    "2df8e 00ce006a" "2df92 00ce006a" "2df96 00010000" "57fd4 00020000"
run armed_outside  "2df92 00100010" "57fd4 00010000"
run examine_click  "2df8e 00ce006a" "2df96 00010000" "57fea 00010000"
run examine_noclick "2df92 00ce006a" "57fea 00010000"
