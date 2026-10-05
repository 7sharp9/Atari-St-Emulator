#!/bin/sh
# gates.sh : fresh runs of every gate of this directory (about 12 minutes), then gates_check.py counts them. Logs go to $FFA_OUT (default scratchpad/finalfight/objects/out),
# the MAME run directory to $FFA_RUN. Nothing is reused: the out directory's *.log are removed first. Needs sb_boss, sb_s1, sb_s6 in scratchpad/finalfight/stage/run/sta/ffightuc/.
here=$(cd "$(dirname "$0")" && pwd)
. "$here/env.sh"
rm -f "$out"/*.log "$out"/*.lua "$out"/*.png
cd "$here" || exit 1
# fire against the player at 7 offsets, against a fighter at 7 offsets (player parked 160 px away), fighter at +40 for 8 start phases
for d in 0 20 -21 40 -41 60 80; do ./fire_run.sh fd_$d $d > /dev/null; done
for f in 0 28 40 -41 80 -65 64; do ./fire_run.sh ff_$f -160 $f > /dev/null; done
for at in 200 201 202 203 204 205 206 207; do ./fire_run.sh fp_$at -160 40 $at > /dev/null; done
# natural bottle (thrower spawned at three phases) and punches at the bottle in flight
./bottle_run.sh bt1 200 90 > /dev/null; ./bottle_run.sh bt2 207 b0 > /dev/null; ./bottle_run.sh bt4 221 70 > /dev/null
for pr in 286 290 294 298 302 306; do ./bottle_hit_run.sh bh_$pr $pr > /dev/null; done
./deflect_run.sh df1 20 40 > /dev/null; ./deflect_run.sh df2 24 30 > /dev/null; ./deflect_run.sh df3 16 48 > /dev/null; ./deflect_run.sh df4 20 80 > /dev/null
# weapons: pickup of kinds 0, 2, 3, 4 and the shell hitting the player (kind 3 flying at Cody, owner = a pool 4 record, +14 = ground, y = ground + $46)
for k in 0 2 3 4; do ./pick_run.sh pk$k $k > /dev/null; done
FFA_LOAD=sb_s1 FFA_LOG="$out/sh2.log" FFA_STOP=330 FFA_KILL=200 FFA_SPAWNS="200:6:3:0:0:240:7c" FFA_POKES="200:@46:01:1,200:@14:0036:2,200:@76:9a68:2" \
  FFA_PIN="190-330:P:1c0:36" FFA_POOLS="P:ff8568:c0:1" FFA_TAG=sh2 ./run.sh "$here/sp.lua" > /dev/null 2>&1
# kind A/B: parked camera, the kind's records zeroed in run B (their addresses are fixed by the area init)
./ab.sh k6 02 02 e70 1000 "ffa8a8+ffa968+ffaa28+ffaae8+ffaba8+ffac68" > /dev/null
./ab.sh k7 02 01 1380 300 "ffa728+ffa7e8+ffa8a8+ffa968+ffaa28+ffaae8+ffaba8+ffac68+ffad28+ffade8" > /dev/null
./ab.sh k9 04 00 7b0 900 "ffad28+ffac68+ffaba8" > /dev/null
./ab.sh ka 04 00 7b0 900 "ffaf68+ffaea8+ffade8" > /dev/null
./ab.sh k10 03 00 300 700 "ffade8+ffad28+ffac68+ffaba8+ffaae8" > /dev/null
./ab.sh k3b 03 00 7c0 1000 "ffaf68" "scr2:90c000:4000" > /dev/null
# kind 0 id 0 palette flicker: reference and hidden
for v in ref hid; do HIDE=""; [ $v = hid ] && HIDE="100:ffad28"
  FFA_LOAD=sb_s1 FFA_LOG="$out/k0_$v.log" FFA_STOP=200 FFA_POKES="1:ff80be:00:1,1:ff80bf:01:1,1:ff8000:0004:2" FFA_GFX="pal:914000:1800" FFA_HIDE="$HIDE" FFA_SHOT=150 FFA_TAG=k0_$v ./run.sh "$here/sp.lua" > /dev/null 2>&1
done
# kinds $1e (sb_boss, shadow flag held) and $1f (stage 3 area 1 ANDORE): hide diffs
for v in ref hid; do HIDE=""; [ $v = hid ] && HIDE="20:ffaf68"
  FFA_LOAD=sb_boss FFA_LOG="$out/k1e_$v.log" FFA_STOP=30 FFA_HOLDA="5-30:ff1308:1:1" FFA_HIDE="$HIDE" FFA_SHOT=26 FFA_TAG=k1e_$v ./run.sh "$here/sp.lua" > /dev/null 2>&1
done
for v in ref hid; do HIDE=""; [ $v = hid ] && HIDE="702:ffb0e8"
  FFA_LOAD=sb_s1 FFA_LOG="$out/k1f_$v.log" FFA_STOP=710 FFA_POKES="1:ff80be:03:1,1:ff80bf:01:1,1:ff8000:0004:2" FFA_HEAL=1 FFA_HIDE="$HIDE" FFA_SHOT=706 FFA_TAG=k1f_$v ./run.sh "$here/sp.lua" > /dev/null 2>&1
done
# kind $e: flag and camera-2 x poked; bonus stage 6 natural run
FFA_LOAD=sb_s1 FFA_LOG="$out/e1.log" FFA_STOP=420 FFA_HOLDA="200-400:ff8492:1100:2,200-201:ff12fc:1:1" FFA_GFX="scr3:910000:4000" FFA_TAG=e1 ./run.sh "$here/sp.lua" > /dev/null 2>&1
FFA_LOAD=sb_s6 FFA_LOG="$out/b6.log" FFA_STOP=900 FFA_TAG=b6 ./run.sh "$here/sp.lua" > /dev/null 2>&1
"$py" "$here/gates_check.py" "$out"
