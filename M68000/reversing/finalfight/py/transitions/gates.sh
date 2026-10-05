#!/bin/sh
# gates.sh: regenerate every log the transition gates read, then run gates.py (23 gates). About 2.5 minutes (the cold boot and the idle TIME run go in the background).
# Needs the stage-0 states sb_boss and sb_s1 (py/stage/run.sh boss, stage1: scratchpad/finalfight/stage/run/sta/ffightuc/); they are copied into this run directory.
# Own run directory: FFT_RUN / FFT_OUT (default <repo>/scratchpad/finalfight/transitions/{run,out}).
here=$(cd "$(dirname "$0")" && pwd)
root=${M68000_ROOT:-$here}
while [ ! -f "$root/reversing/finalfight/lua/stagebot.lua" ] && [ "$root" != "/" ]; do root=$(dirname "$root"); done
export FFT_RUN=${FFT_RUN:-$root/scratchpad/finalfight/transitions/run} FFT_OUT=${FFT_OUT:-$root/scratchpad/finalfight/transitions/out}
mkdir -p "$FFT_RUN/sta/ffightuc" "$FFT_OUT"
for s in sb_boss sb_s1; do
  [ -f "$FFT_RUN/sta/ffightuc/$s.sta" ] || cp "$root/scratchpad/finalfight/stage/run/sta/ffightuc/$s.sta" "$FFT_RUN/sta/ffightuc/" || exit 1
done
R="$here/run.sh"
PLAN1=$root/reversing/finalfight/lua/plans/plan1.lua
# long runs in the background: a cold boot with taps, and the idle run to the natural TIME 0 (the bot is off, so FF_STOP ends it)
FF_PLAN=$PLAN1 FF_BOT_START=2450 FF_BOT_STOPF=12000 "$R" trans g_cold > "$FFT_OUT/g_cold.stdout" 2>&1 &
FF_PLAN=$PLAN1 FF_BOT_START=99999 FF_STOP=17600 "$R" trans g_timezero > "$FFT_OUT/g_timezero.stdout" 2>&1 &
# from sb_boss: the DAMND area clear to stage 1 area 0 (resumed lineage), 2 s per 1000 frames
FF_LOAD=sb_boss FF_BOT_START=0 FF_BOT_STOPF=12700 "$R" trans g_boss > "$FFT_OUT/g_boss.stdout" 2>&1
FF_LOAD=sb_boss FF_BOT_START=0 FF_BOT_STOPF=8500 "$R" trans g_hook > "$FFT_OUT/g_hook.stdout" 2>&1
# E1: raise the camera right limit 1078(A5) from $0b00 to $0c00 at 11100
FF_LOAD=sb_boss FF_BOT_START=0 FF_BOT_STOPF=11400 FF_TR_POKE="11100:ff8436:0c00" "$R" trans g_limit > "$FFT_OUT/g_limit.stdout" 2>&1
# E2: freeze the camera with 278(A5)=1 from 11900 to 12100 in stage 1 area 0 (baseline: g_boss)
FF_LOAD=sb_s1 FF_BOT_START=0 FF_BOT_STOPF=12400 FF_TR_POKE="11900:ff8116:01,12100:ff8116:00" "$R" trans g_lock > "$FFT_OUT/g_lock.stdout" 2>&1
# E4: 291(A5)=1 at 12000 (player state 12)
FF_LOAD=sb_s1 FF_BOT_START=0 FF_BOT_STOPF=12700 FF_TR_POKE="12000:ff8123:01" "$R" trans g_s12 > "$FFT_OUT/g_s12.stdout" 2>&1
# E5: a jump at 11800, 297(A5)=1 at 11820 in the air (bot off)
FF_STOP=12300 FF_LOAD=sb_s1 FF_BOT_START=99999 FF_TR_HOLD="11800-11803:b2:1" FF_TR_POKE="11820:ff8129:01" "$R" trans g_air > "$FFT_OUT/g_air.stdout" 2>&1
# E6: 191(A5)=3 and 297(A5)=1 in stage 1 (the last area of stage 1 is area 3): bonus stage 1, then stage 2
FF_LOAD=sb_s1 FF_BOT_START=0 FF_BOT_STOPF=15200 FF_TR_POKE="11800:ff80bf:03,11801:ff8129:01" "$R" trans g_bonus > "$FFT_OUT/g_bonus.stdout" 2>&1
# E7: stage 1 area 1 (state saved at 24000 by a bot run from sb_s1): 297(A5)=1 at 24020; the area has no walk-out (state 10 sub $a) and its camera hook ends it
FF_LOAD=sb_s1 FF_BOT_START=0 FF_BOT_STOPF=24000 FF_SAVE=c_s1a1 FF_TR_TAPS=0 FF_TR_POOLS=0 "$R" trans g_mk_s1a1 > "$FFT_OUT/g_mk_s1a1.stdout" 2>&1
FF_LOAD=c_s1a1 FF_BOT_START=0 FF_BOT_STOPF=24700 FF_TR_POKE="24020:ff8129:01" "$R" trans g_s1a1 > "$FFT_OUT/g_s1a1.stdout" 2>&1
# fade flag 140(A5) and the walked-off flag 166(A6) during the DAMND area clear (word taps: lo even, hi odd)
FF_LOAD=sb_boss FF_BOT_START=0 FF_BOT_STOPF=11620 FF_PT_W="ff808c-ff808d,ff860e-ff860f,ff8128-ff8129" FF_PT_LO=11264 FF_PT_HI=11620 "$R" pt g_fade > "$FFT_OUT/g_fade.stdout" 2>&1
wait
"$root/.venv/bin/python" "$here/gates.py" "$FFT_OUT"
