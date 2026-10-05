#!/bin/sh
# run_chars.sh <ch> : every per-character run for character <ch> (0 Guy, 1 Cody, 2 Haggar) from state dch<ch>_1900 (run/make_states.sh): logs $FFD_OUT/ch<ch>_*.txt, wj_ch<ch>_*.txt, ...
# Each run is a pdrive.lua run (about 3 to 8 s): the dummy is Bred (pool-2 record 12, hp $300) moved next to the player; GOD makes the player unhittable.
here=$(cd "$(dirname "$0")" && pwd); d=$(cd "$here/../.." && pwd); ch=$1
. "$d/run/env.sh"

R="sh $d/run/crun.sh"
E=$d/lua/extra_dummy.lua; E2=$d/lua/extra_dummy2.lua; E3=$d/lua/extra_dummy3.lua
FF_GOD=1 FF_EXTRA=$E FF_DX=24 $R ch${ch}_c1 $ch c1 200
FF_GOD=1 FF_EXTRA=$E FF_DX=24 $R ch${ch}_j1 $ch j1 650
FF_GOD=1 FF_EXTRA=$E FF_DX=24 $R ch${ch}_j2 $ch j2 560
FF_GOD=1 FF_EXTRA=$E FF_DX=24 $R ch${ch}_j3 $ch j3 150
FF_GOD=1 FF_EXTRA=$E FF_DX=-24 $R ch${ch}_j4 $ch j4 150
for dx in 30 -30; do FF_GOD=1 FF_EXTRA=$E FF_DX=$dx $R ch${ch}_s1_$dx $ch s1 330; done
for v in a b c d e; do FF_GOD=1 FF_EXTRA=$E3 FF_DX=26 $R ch${ch}_g3$v $ch g2$v 300; done
FF_GOD=1 FF_EXTRA=$E3 FF_DX=24 $R ch${ch}_bg1 $ch bg1 140
case $ch in 0) bg=bgG;; 1) bg=bg1;; 2) bg=bgH;; esac
FF_GOD=1 FF_EXTRA=$E3 FF_DX=24 $R bg_ch$ch $ch $bg 300
for seed in 1 2; do FF_SEED=$seed FF_N=3000 FF_GOD=1 FF_EXTRA=$E2 FF_DX=24 $R ch${ch}_rand$seed $ch rand1 3000; done
FF_KILL=1 FF_KEEP=99 FF_GOD=1 $R a1_ch$ch $ch a1 1000 FF_KILL=1 FF_KEEP=99
FF_KILL=1 FF_KEEP=99 FF_GOD=1 $R walk_ch$ch $ch walk1 620 FF_KILL=1 FF_KEEP=99
# wall jump probe (plan wj1): walk up and right into the oil drum (prop kind 8 at x $2f0, ground line $3f), jump right, press jump again in the air and hold it
wj() { # name t0 dt hold b1 left down2
 FF_WJ_END=700 FF_WJ_T0=$2 FF_WJ_DT=$3 FF_WJ_HOLD=$4 FF_WJ_B1=$5 FF_WJ_LEFT=$6 FF_WJ_DOWN2=$7 FF_KILL=1 FF_KEEP=99 FF_GOD=1 FF_EXTRA=$d/lua/extra_enemy.lua \
   sh $d/run/crun.sh $1 $ch wj1 400 FF_KILL=1 FF_KEEP=99 FF_WJ_T0=$2 FF_WJ_DT=$3 FF_WJ_HOLD=$4 FF_WJ_B1=$5 FF_WJ_LEFT=$6 FF_WJ_DOWN2=$7 FF_WJ_END=700
}
wj wj_ch${ch}_a 300 12 14 -1 -1 -1
wj wj_ch${ch}_b1grip 300 12 14 316 -1 -1
wj wj_ch${ch}_left 300 12 14 -1 318 -1
wj wj_ch${ch}_down 300 12 14 -1 -1 316
# Haggar's jump slam in the grapple (b2, then b1 within 18 frames)
if [ "$ch" = 2 ]; then for b in 68 74 80; do FF_GOD=1 FF_EXTRA=$E3 FF_DX=26 $R ch2_g4_$b 2 g2f_$b 300; done; fi
