#!/usr/bin/env bash
# class_a_nat.sh: opponent class $a reached by a real sword click (no category poke): k120 forest op 8's first tree is claimed by one
# labelled poke (w 4ddc4 0b220000: tree word 2 worker_obj := the lead's record offset $b22, word 4 kept 0), so $4342 chains op 8's markers
# into cell (33,87); the sword click on that minimap cell makes $4a7a take the marker (204 := 8, 24 := $b142 = record $4cca8) and
# $4bc8 classify it $a.  Then: arm "ctl" (no poke) and arm "kill" (marker byte 5 := $ff) from the parked-marker snapshot.
# Output ${PM_WORK:-scratchpad/pmwork}/orders/man/ (mk8_*).  Steps: man_click.sh (capture), 6 x 2M hits, 6 x 5M, ctl/kill 10M.
set -e
HERE=$(cd "$(dirname "$0")" && pwd)
ROOT=${M68000_ROOT:-$HERE}
while [ ! -f "$ROOT/tools/rdis.py" ]; do ROOT=$(dirname "$ROOT"); [ "$ROOT" = / ] && { echo "no repo root"; exit 1; }; done
cd "$ROOT"
O=${PM_WORK:-scratchpad/pmwork}/orders/man; mkdir -p "$O"
run() { ATARI_NOTRACE=1 dotnet exec bin/Debug/net8.0/M68000.dll resume "$1" repl < "$2" 2>&1 | grep -v "^mouse\|first -1\|^$"; }
POKE="w 4ddc4 0b220000" "$HERE/man_click.sh" k120 33 87 52688 mk8_poke | tail -2
{ echo "disk scratchpad/powermonger.st"; echo "watch 5178c 2"
  for i in 1 2 3 4 5 6; do echo "hits 2000000 4a7a 4bc8 4de2 4eca 4d68 5150 1518a"; echo "m 516c0 2"; echo "m 5178c 2"; echo "m 4cca8 16"; echo "snap $O/mk8_d$i.snap"; done
  echo q; } > "$O/chain.cmds"
run "$O/n_mk8_poke_1.snap" "$O/chain.cmds" | grep -v "^---" | tail -40
{ echo "disk scratchpad/powermonger.st"; for i in 1 2 3 4 5 6; do echo "hits 5000000 5150 510e 5124 35f4"; echo "m 4cca8 16"; done; echo "snap $O/mk8_g.snap"; echo q; } > "$O/park.cmds"
run "$O/mk8_d6.snap" "$O/park.cmds" | tail -30
echo "== ctl"; printf 'disk scratchpad/powermonger.st\nhits 10000000 5150 510e 5124 35f4\nm 4ccac 4\nm 516c0 2\nq\n' > "$O/ctl.cmds"; run "$O/mk8_g.snap" "$O/ctl.cmds"
echo "== kill"; printf 'disk scratchpad/powermonger.st\nw 4ccac 00ff1600\nhits 10000000 5150 510e 5124 35f4\nm 4ccac 4\nm 516c0 2\nq\n' > "$O/kill.cmds"; run "$O/mk8_g.snap" "$O/kill.cmds"
