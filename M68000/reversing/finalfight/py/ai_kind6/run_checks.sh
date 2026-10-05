#!/bin/sh
# run_checks.sh: fresh runs and all gates (about 15 minutes). Outputs stay in $K6_RUN_DIR.
dir=$(cd "$(dirname "$0")" && pwd)
run=${K6_RUN_DIR:-$dir/../../../../scratchpad/finalfight/p3/d/run}; mkdir -p "$run"; run=$(cd "$run" && pwd); export K6_RUN_DIR=$run
rm -f "$run"/*_frames.bin "$run"/hits_*.txt
[ -f "$run/sta/ffightuc/k6_pre.sta" ] || "$dir/make_pre.sh"
"$dir/runids.sh" 0 48; "$dir/runids.sh" 1 48
python3 "$dir/gate_dmg.py"
for c in 0 1; do
  K6_TAG=bb$c K6_FRAMES=9000 K6_RESPAWN=60 K6_IMMORTAL=1 K6_BOT=1 K6_REL=1 K6_SPAWN="$c:0:300:48" "$dir/ffrun_k6.sh" "$dir/k6run.lua" 300 >/dev/null 2>&1
done
python3 "$dir/gate_score.py" "$run/bb0_frames.bin" "$run/bb1_frames.bin"
python3 "$dir/stat.py" "$run/bb0_frames.bin"; python3 "$dir/stat.py" "$run/bb1_frames.bin"
python3 "$dir/decide2.py" "$run/bb0_frames.bin"; python3 "$dir/decide2.py" "$run/bb1_frames.bin"
for c in 0 1; do
  K6_HIT_OUT=$run/hits_dodge_$c.txt K6_BP="3a454|E d=%x st=%x|b@(a3+0x60),b@(a3+2);3a48a|N d=%x rnd=%x mask=%x|b@(a3+0x60),d0,d1;3a492|Y d=%x|b@(a3+0x60)" \
    K6_REL=1 K6_TAG=dg$c K6_FRAMES=9000 K6_RESPAWN=60 K6_IMMORTAL=1 K6_BOT=1 K6_SPAWN="$c:0:300:48" FF_MAMEARGS="-debug -debugger none" "$dir/ffrun_k6.sh" "$dir/k6hit.lua" 300 >/dev/null 2>&1
  python3 "$dir/hitlog.py" dodge "$run/hits_dodge_$c.txt"
  K6_HIT_OUT=$run/hits_mask_$c.txt K6_BP="3a53a|M ch=%x d96=%x mask=%x rnd=%x|b@(a6+0x14),b@(a6+0x60),d1,d0" \
    K6_REL=1 K6_TAG=mk$c K6_FRAMES=9000 K6_RESPAWN=60 K6_IMMORTAL=1 K6_SPAWN="$c:0:300:48" FF_MAMEARGS="-debug -debugger none" "$dir/ffrun_k6.sh" "$dir/k6hit.lua" 300 >/dev/null 2>&1
  python3 "$dir/hitlog.py" mask "$run/hits_mask_$c.txt"
done
