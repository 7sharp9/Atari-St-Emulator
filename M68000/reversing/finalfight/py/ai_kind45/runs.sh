#!/bin/sh
# Regenerate every trace the gates read. Output directory $AI45_OUT (default scratchpad/finalfight/p3/c/out), MAME run dir $AI45_RUN.
# Each run: load ff_enemies, orphan its five live enemies at relative frame 0, spawn one fighter at frame 2 (drv.lua FF_SPAWN =
# "kind:+20:+21:level:x:y@frame", negative x = offset right of Cody), keep Cody alive (FF_HEAL), optional Cody inputs (plan_*.lua).
here=$(cd "$(dirname "$0")" && pwd)
root=$(cd "$here/../../../.." && pwd)
OUT=${AI45_OUT:-$root/scratchpad/finalfight/p3/c/out}
mkdir -p "$OUT"
run() { # name frames spawn [plan]
  name=$1; n=$2; spawn=$3; plan=$4
  if [ -n "$plan" ]; then pl="FF_PLAN=$here/$plan"; else pl="FF_PLAN="; fi
  env FF_LOAD=ff_enemies FF_N=$n FF_HEAL=1 FF_KILL=0 FF_SPAWN="$spawn" FF_OUTF=$OUT/$name.bin $pl FF_GFXDUMP="$GFX" \
    "$here/run.sh" drive "$here/drv.lua" 300 2>&1 | grep -i 'error'
}
GFX=
for s in 0 1 2; do run k4n$s 3000 "4:$s:0:0:-110:44@2"; run k4t$s 2400 "4:$s:0:0:-110:44@2" plan_tap.lua; done
for e in 2 4 6 8; do run k4e$e 300 "4:0:$e:0:-100:44@2"; done
run blk4 900 "4:0:0:0:1290:63@2"
for g in g1 g3 g4 g5; do run k4$g 500 "4:0:0:0:-30:47@2" plan_$g.lua; done
run k4L20 1200 "4:2:0:20:-110:44@2"
run k5m0 1500 "5:0:0:0:-30:47@2"
run k5m1 2500 "5:1:0:0:-30:47@2"
run k5u0 2500 "5:0:0:0:-30:47@2" plan_tap.lua
run k5u1 2500 "5:1:0:0:-30:47@2" plan_tap.lua
run k5n0 3000 "5:0:0:0:-110:44@2"
run k5e2 400 "5:0:2:0:-30:47@2"
run blk5 900 "5:0:0:0:1290:63@2"
for g in g1 g2 g3 g4 g5 g6; do run k5$g 400 "5:0:0:0:-30:47@2" plan_$g.lua; done
run k5L7 1200 "5:0:0:7:-30:47@2"
run cull5 60 "5:0:0:0:1608:44@2"
run cull5b 60 "5:0:0:0:1500:44@2"
# names: the HUD name appears a few frames after the first hit on Cody (first hit at relative frame 67 for kind 4, 39 for kind 5 sub 0, 23 for sub 1)
GFX=80; for s in 0 1 2; do run nm4$s 82 "4:$s:0:0:-110:44@2"; done
GFX=50; run nm50 52 "5:0:0:0:-30:47@2"
GFX=40; run nm51 42 "5:1:0:0:-30:47@2"
GFX=
# baseline without a spawn
env FF_LOAD=ff_enemies FF_N=900 FF_OUTF=$OUT/e900.bin "$here/run.sh" drive "$here/drv.lua" 300 2>&1 | grep -i error
# saved states in $AI45_RUN/sta/ffightuc/: p3c_k4_goriber (end of relative frame 40), p3c_k5_hollywood (60)
env FF_LOAD=ff_enemies FF_N=60 FF_HEAL=1 FF_KILL=0 FF_SAVE_AT=40 FF_SAVE_NAME=p3c_k4_goriber FF_SPAWN="4:0:0:0:-110:44@2" FF_OUTF=$OUT/save_k4.bin "$here/run.sh" drive "$here/drv.lua" 120 2>&1 | grep -i error
env FF_LOAD=ff_enemies FF_N=60 FF_HEAL=1 FF_KILL=0 FF_SAVE_AT=60 FF_SAVE_NAME=p3c_k5_hollywood FF_SPAWN="5:0:0:0:-30:47@2" FF_OUTF=$OUT/save_k5.bin "$here/run.sh" drive "$here/drv.lua" 120 2>&1 | grep -i error
for f in "$OUT"/*.bin; do gzip -f "$f"; done
echo done
