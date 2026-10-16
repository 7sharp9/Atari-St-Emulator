#!/usr/bin/env bash
# A $84/$92 melee man from the real posture-5 trade run, not a labelled poke on pm88_f1.
# From scratchpad/pm162/posture/trade/at63f4.snap with trade5_fwd.sh's P5B84 arm (posture 5
# at $63f4, byte 44 as the trade writes it), run to about 865.5M cumulative steps (the
# men's byte 31 is $32 from 864.8M to 866.6M), point the camera at their cells (38,74)
# (labelled poke `w 4bb3a 0026004a`), settle, snap the state at $f898 and the next $f898,
# then score the 6 melee men's byte-44-dependent pixels with diff.fsx on the one capture
# given twice: the true render against byte 44 + 1 and against the aligned frame (b44 0).
#   real_melee84.sh      (repo root found via tools/rdis.py; port/godot/logic built first)
# Output in ${PM_WORK:-scratchpad/pm165}/real84.
set -eu
here=$(cd "$(dirname "$0")" && pwd); d=$here
while [ ! -f "$d/tools/rdis.py" ]; do d=$(dirname "$d"); [ "$d" = / ] && { echo "no repo root"; exit 1; }; done
cd "$d"
O=$d/${PM_WORK:-scratchpad/pm165}/real84; mkdir -p "$O"
PY="uv run python"
# WINDOW=1: first watch the 12 men's records over 60M steps (about 4 min) and print the melee window
if [ -n "${WINDOW:-}" ]; then
  { echo 'disk scratchpad/powermonger.st'; echo 'w 51974 00050002'; echo 'w 4e6f4 03000000'; echo 'w 4e6ec 00050000'
    echo 'bp 6500 400000'; echo 'watch 53b6e 600'; for i in 1 2 3 4 5 6; do echo 'hits 10000000 6522'; done; echo q; } |
    ATARI_NOTRACE=1 dotnet exec bin/Debug/net8.0/M68000.dll resume scratchpad/pm162/posture/trade/at63f4.snap repl \
    > "$O/watch.out" 2> "$O/watch.err" || true
  grep -A1 'hits over' "$O/watch.out" | grep 6522
  $PY "$here/melee_window.py" "$O/watch.err" | tail -3
fi
{ echo 'disk scratchpad/powermonger.st'; echo 'w 51974 00050002'; echo 'w 4e6f4 03000000'; echo 'w 4e6ec 00050000'
  echo 'bp 6500 400000'; echo 's 18300000'; echo 'w 4bb3a 0026004a'; echo 's 2000000'; echo 'u f898 5000000'
  echo "snap $O/mb_0.snap"; echo 'bpc f898 1 5000000'; echo "snap $O/mb_1.snap"; echo q; } > "$O/mb.cmds"
ATARI_NOTRACE=1 dotnet exec bin/Debug/net8.0/M68000.dll resume scratchpad/pm162/posture/trade/at63f4.snap repl \
  < "$O/mb.cmds" > "$O/mb.out" 2>&1 || true
[ -f "$O/mb_1.snap" ] || { echo "no next frame: $(grep -m1 -E 'Step failed|Unhandled|fault' "$O/mb.out")"; exit 1; }
$PY reversing/powermonger/py/snap2ram.py "$O/mb_0.snap" "$O/mb_1.snap" >/dev/null
for i in 0 1; do $PY reversing/powermonger/py/dump_frame.py "$O/mb_$i.ram" "$O/mb_$i.json" | tail -1; done
# the melee men in view: byte 31 $32 and byte 44 $84 (132) / $92 (146)
$PY "$here/find_men.py" "$O/mb_0.ram" 0 | grep -E 'b31 \$32 .* b44 (132|146) ' > "$O/melee.txt" || true
cat "$O/melee.txt"
sel() { grep -E "b44 $1 " "$O/melee.txt" | sed -E 's/.*\$([0-9a-f]{5}) b6.*/\1/' | paste -sd, -; }
M84=$(sel 132); M92=$(sel 146); ALL=$(echo "$M84,$M92" | sed 's/^,//;s/,$//')
[ -n "$M84" ] && [ -n "$M92" ] || { echo "no \$84 and \$92 melee men in view"; exit 1; }
A=$O/mb_0.json+$O/mb_1.json; B=$O/./mb_0.json+$O/./mb_1.json
for w in "b44:1:$ALL" "b44:-132:$M84" "b44:-146:$M92"; do
  echo "== $w"
  echo -n "  true render: "; WRONG_SIDE=ctl WRONG=$w dotnet fsi "$here/diff.fsx" 0 "$A" "$B" | tail -1 | sed 's/ | without.*//'
  echo -n "  altered:     "; WRONG=$w dotnet fsi "$here/diff.fsx" 0 "$A" "$B" | tail -1 | sed 's/ | without.*//'
done
