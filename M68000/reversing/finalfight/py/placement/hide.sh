#!/bin/sh
# hide.sh <state> <shotname> [hex record addresses, comma list]
here=$(cd "$(dirname "$0")" && pwd)
root=$(cd "$here/../../../.." && pwd)
ff="$root/reversing/finalfight"
out=${BB_OUT:-$root/scratchpad/finalfight/placement/out}
run=${BB_RUN:-$root/scratchpad/finalfight/placement/run}
mkdir -p "$run/cfg" "$run/nvram" "$run/sta" "$run/snap" "$out/tmp"
export FF_DIR="$ff/lua" FF_OUT="$out" SDL_VIDEODRIVER=dummy FF_SAVE_FRAME=99999 FF_STOP=60000
export FF_LOAD="$1" FF_HIDE_SHOT="$2" FF_HIDE="$3"
cd "$run" || exit 1
exec mame ffightuc -rompath "${FF_ROMS:-$HOME/mame-roms}" -cfg_directory "$run/cfg" -nvram_directory "$run/nvram" \
  -state_directory "$run/sta" -snapshot_directory "$run/snap" -video none -sound none -nothrottle -seconds_to_run 900 -autoboot_script "$here/hide.lua"
