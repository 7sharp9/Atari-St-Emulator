#!/bin/sh
# bossrec.sh <boss kind 1..5 | 7 | e> : replay the stage of that pool-4 boss from its whole-game state with the stage 2 to 5 bot options, save the state one frame before the boss record
# appears (bb_k<kind>, FF_SAVE_FRAME), record work RAM per frame from BR_RECLO (py/boss/dd.py format, ranges $BR_RECR) to the stage change, log the run.
# Own run directory ($BR_ROOT/run_k<kind>, the sb_s* states copied in) and output ($BR_ROOT/out_k<kind>): rec.bin, s.log, bb_k<kind>.sta in the run dir. The end state is saved as rr_s<new stage byte>,
# so the sb_s* states are never overwritten. 7: the stage 2 area 0 clear with the pool-4 kind 7 carrier (to frame 55,400); e: the stage 5 area 0 elevator scene (player state 12, frames 210,500 to 213,500). Compare s.log with the lineage's old log (BR_OLD) to check the replay took the same trajectory.
here=$(cd "$(dirname "$0")" && pwd)
root=$(cd "$here/../../../.." && pwd)
st=$root/scratchpad/finalfight/stage
BR_ROOT=${BR_ROOT:-$root/scratchpad/finalfight/bossrec}
BR_RECR=${BR_RECR:-ff12e0-ff1300,ff8000-ffb300}
k=$1
# kind: start state, stage byte, spawn frame, first recorded frame, old log, options (stage 1 was played with PROPS only, stages 2 to 5 with the README's options)
opts="FF_BOT_LANEFIX=1 FF_BOT_LURE=1 FF_BOT_UNSTICK=1 FF_BOT_HP0=1"
case "$k" in
  1) s=sb_s1;   sb=1; sp=38980;  lo=38979;  old=$st/out/stage2.log; opts= ;;
  2) s=sb_s2a2; sb=2; sp=56841;  lo=56840;  old=$st/out5/a2.log ;;
  3) s=sb_s3;   sb=3; sp=79161;  lo=79160;  old=$st/out5/s3.log ;;
  4) s=sb_s4;   sb=4; sp=87005;  lo=193300; old=$st/out5/s4.log ;;
  5) s=sb_s5;   sb=5; sp=277309; lo=285600; old=$st/out5/s5.log ;;
  7) s=sb_s2;   sb=2; sp=52760;  lo=52700;  old=$st/out5/to_a2.log; BR_MAXF=${BR_MAXF:-55400} ;;
  e) s=sb_s5;   sb=5; sp=210500; lo=210500; old=$st/out5/s5.log; BR_MAXF=${BR_MAXF:-213500} ;;
  *) echo "usage: $0 <kind 1..5 | 7 | e>" >&2; exit 2 ;;
esac
lo=${BR_RECLO:-$lo}
run=$BR_ROOT/run_k$k; out=$BR_ROOT/out_k$k
mkdir -p "$run/sta/ffightuc" "$out"
cp "$st/run/sta/ffightuc/$s.sta" "$run/sta/ffightuc/"
env $opts FF_BOT_PROPS=1 FF_LOAD=$s FF_BOT_START=0 FF_BOT_LEAVE=$sb FF_SAVE_PREFIX=rr_s FF_BOT_STOPF=${BR_MAXF:-300000} \
  FF_SAVE=bb_k$k FF_SAVE_FRAME=$((sp - 1)) FF_BOT_REC="$out/rec.bin" FF_BOT_RECLO=$lo FF_BOT_RECR="$BR_RECR" FF_BOT_LOG="$out/s.log" \
  FFS_RUN="$run" FFS_OUT="$out" sh "$here/run.sh" custom > "$out/run.out" 2>&1
tail -1 "$out/s.log"
if [ -f "$old" ]; then
  n=$(grep -c . "$out/s.log"); echo "log lines $n; first difference from $old:"
  cmp "$out/s.log" "$old" | head -1
fi
