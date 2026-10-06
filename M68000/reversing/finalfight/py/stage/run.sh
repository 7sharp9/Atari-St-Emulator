#!/bin/sh
# run.sh <step> : play stage 0 with lua/stagebot.lua (README.md here). Own MAME run directory ($FFS_RUN) and output directory ($FFS_OUT), so several
# can run at once. Steps (each prints where its log and state went):
#   boss     cold boot, kill Bred (plans/plan1.lua), bot to camera x $aa0 (stage 0 area 2 trigger), saves state sb_boss   (about 8300 frames, 45 s)
#   stage1   from sb_boss: bot through DAMND and the rest of area 2 to stage byte 1, saves state sb_s1               (about 2000 frames)
#   custom   FF_LOAD/FF_BOT_* taken from the environment as they are
# Environment: FFS_RUN (default scratchpad/finalfight/stage/run), FFS_OUT (default scratchpad/finalfight/stage/out), FF_BOT_GOD=0 turns the health poke off.
# FFS_FRAMESKIP (default 10): MAME skips drawing 9 frames in 10, about 12% faster with byte-identical RAM, gfx RAM and logs (README.md "Lua cost"); a PNG taken at a stop frame can be a stale
# frame, so set FFS_FRAMESKIP=0 for a run whose screenshots matter. -joystickprovider none saves 0.5 s of startup.
here=$(cd "$(dirname "$0")" && pwd)
ff=$(cd "$here/../.." && pwd)
root=$(cd "$ff/../.." && pwd)
run=${FFS_RUN:-$root/scratchpad/finalfight/stage/run}
out=${FFS_OUT:-$root/scratchpad/finalfight/stage/out}
mkdir -p "$run/cfg" "$run/nvram" "$run/sta" "$run/snap" "$out/tmp"
export FF_DIR="$ff/lua" FF_OUT="$out" SDL_VIDEODRIVER=dummy
export FF_SAVE_FRAME=99999 FF_STOP=${FF_STOP:-1000000}
step=${1:-boss}
case "$step" in
  boss)   export FF_PLAN="$ff/lua/plans/plan1.lua" FF_BOT_START=2450 FF_BOT_CAM=2720 FF_SAVE=sb_boss FF_BOT_LOG="$out/boss.log" ;;
  stage1) export FF_LOAD=sb_boss FF_BOT_START=0 FF_BOT_STAGE=1 FF_BOT_STOPF=30000 FF_SAVE=sb_s1 FF_BOT_LOG="$out/stage1.log" ;;
  custom) ;;
  *) echo "usage: $0 boss | stage1 | custom" >&2; exit 2 ;;
esac
cd "$run" || exit 1
exec mame ffightuc -rompath "${FF_ROMS:-$HOME/mame-roms}" -cfg_directory "$run/cfg" -nvram_directory "$run/nvram" \
  -state_directory "$run/sta" -snapshot_directory "$run/snap" -video none -sound none -nothrottle -frameskip "${FFS_FRAMESKIP:-10}" -joystickprovider none ${FF_MAMEARGS} \
  -seconds_to_run "${FFS_SECONDS:-6000}" -autoboot_script "$ff/lua/stagebot.lua"
