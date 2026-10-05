#!/bin/sh
# run.sh <script.lua> [seconds] : headless MAME on ffightuc, no debugger, own run dir (FFA_RUN, default scratchpad/finalfight/objects/run; logs go to FFA_OUT, default scratchpad/finalfight/objects/out). States are looked up in <run>/sta/ffightuc/
# (copied from scratchpad/finalfight/stage/run/sta/ffightuc/ when missing). FFA_DEBUG=1 adds "-debug -debugger none" (breakpoints; cold boots only, see the brief).
here=$(cd "$(dirname "$0")" && pwd)
. "$here/env.sh"
export FF_DIR="$root/reversing/finalfight/lua" SDL_VIDEODRIVER=dummy FFA_HERE="$here"
mkdir -p "$run/cfg" "$run/nvram" "$run/sta/ffightuc" "$run/snap" "$out"
for s in "$root"/scratchpad/finalfight/stage/run/sta/ffightuc/sb_boss.sta "$root"/scratchpad/finalfight/stage/run/sta/ffightuc/sb_s1.sta "$root"/scratchpad/finalfight/stage/run/sta/ffightuc/sb_s2.sta "$root"/scratchpad/finalfight/stage/run/sta/ffightuc/sb_s6.sta; do
  [ -f "$s" ] && [ ! -f "$run/sta/ffightuc/$(basename "$s")" ] && cp "$s" "$run/sta/ffightuc/"
done
dbg=""; [ "$FFA_DEBUG" = 1 ] && dbg="-debug -debugger none"
cd "$run" || exit 1
exec mame ffightuc -rompath "${FF_ROMS:-$HOME/mame-roms}" -cfg_directory "$run/cfg" -nvram_directory "$run/nvram" \
  -state_directory "$run/sta" -snapshot_directory "$run/snap" -video none -sound none -nothrottle $dbg \
  -seconds_to_run "${2:-3000}" -autoboot_script "$1"
