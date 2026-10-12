#!/usr/bin/env bash
# Every graphics cross-check of the F# port in one run, from M68000/:
#   reversing/powermonger/py/xcheck/run.sh
# Needs `dotnet build` of port/godot/logic/PmLogic.fsproj first, and the frame
# RAMs below in scratchpad/ (copied from gpubox in the 154th session; missing
# ones are skipped). Output in ${PM_WORK:-scratchpad/pmwork}/xcheck.
set -u
X=reversing/powermonger/py/xcheck
PY="uv run python"
OUT=${PM_WORK:-scratchpad/pmwork}/xcheck; mkdir -p "$OUT/frames"
export XCHECK_OUT="$OUT"

echo "== frames (dump_frame.py)"
FRAMES=()
for spec in pm88_f1:scratchpad/pm88_f1.ram pm74_late:scratchpad/pm74_late.ram \
            pm78_settle:scratchpad/pm78_settle.ram rot40:scratchpad/pm118/rot40.ram \
            rot90:scratchpad/pm118/rot90.ram rotc0:scratchpad/pm118/rotc0.ram \
            zoom1:scratchpad/pm119/zoom1.ram zoom2:scratchpad/pm119/zoom2.ram \
            zoom3:scratchpad/pm119/zoom3.ram zoom5:scratchpad/pm119/zoom5.ram \
            zoom6:scratchpad/pm119/zoom6.ram zoom7:scratchpad/pm119/zoom7.ram \
            pan_e:scratchpad/pm119/pan_e.ram pan_w:scratchpad/pm119/pan_w.ram; do
  name=${spec%%:*}; ram=${spec#*:}
  if [ -f "$ram" ]; then
    $PY reversing/powermonger/py/dump_frame.py "$ram" "$OUT/frames/$name.json" | tail -1
    FRAMES+=("$OUT/frames/$name.json")
  else
    echo "skip $name: no $ram"
  fi
done

echo "== quadrant walks, synthetic (Fill.planQ0..3 vs walk_q0..q3)"
dotnet fsi $X/quad_fs.fsx >/dev/null && $PY $X/quad_py.py >/dev/null
for q in q0 q1 q2 q3; do
  n=$(wc -l < "$OUT/${q}_fs.txt")
  if cmp -s "$OUT/${q}_fs.txt" "$OUT/${q}_py.txt"; then echo "$q identical ($n px)"; else echo "$q DIFFERS"; fi
done

echo "== blits, synthetic (13 cases; the melee case is expected to differ)"
dotnet fsi $X/blit_fs.fsx >/dev/null && $PY $X/blit_py.py >/dev/null
paste -d'\n' "$OUT/blit_fs.txt" "$OUT/blit_py.txt" | awk 'NR%2{a=$0; next} {n++; if (a==$0) s++; else print "differs: " substr(a, 1, index(a, "|") - 2)} END {print s "/" n " cases identical"}'

echo "== real record stream on pm88_f1 (drawEntitiesArr vs draw_entities)"
dotnet fsi $X/ent_fs.fsx >/dev/null && $PY $X/ent_py.py >/dev/null
n=$(wc -l < "$OUT/ent_fs.txt")
if cmp -s "$OUT/ent_fs.txt" "$OUT/ent_py.txt"; then echo "identical ($n px)"; else echo "DIFFERS"; fi

echo "== renderer baseline (162 lines)"
dotnet fsi $X/baseline.fsx "$OUT/baseline.txt" >/dev/null
if diff -q $X/baseline.txt "$OUT/baseline.txt" >/dev/null; then echo "matches baseline.txt"; else echo "DIFFERS from baseline.txt"; fi

[ ${#FRAMES[@]} -eq 0 ] && exit 0
echo "== draw order (post vs inline) on the zoom-4 frames"
Z4=(); for f in "${FRAMES[@]}"; do case $f in *zoom*|*pan_*) ;; *) Z4+=("$f");; esac; done
dotnet fsi $X/order_test.fsx "${Z4[@]}" | grep -E "^[a-z0-9_]+  cam|inline"
echo "== score.fsx, every frame (inline order, best water tick)"
dotnet fsi reversing/powermonger/py/score.fsx "${FRAMES[@]}" | grep "best tick" | sed 's/frame tick.*best/best/'
echo "== zoom_check.fsx (port records, game corners)"
ZF=(); for f in "${FRAMES[@]}"; do case $f in *zoom*|*pm88_f1*) ZF+=("$f");; esac; done
dotnet fsi $X/zoom_check.fsx "${ZF[@]}" | grep -E "zoom [0-9]|terrain|sprite px"
