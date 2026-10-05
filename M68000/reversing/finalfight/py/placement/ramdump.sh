#!/bin/sh
# ramdump.sh <run dir> <state> <out file>
here=$(cd "$(dirname "$0")" && pwd)
root=$(cd "$here/../../../.." && pwd)
ff="$root/reversing/finalfight"
out=${BB_OUT:-$root/scratchpad/finalfight/placement/out}
run="$1"
export FF_DIR="$ff/lua" FF_OUT="$out" SDL_VIDEODRIVER=dummy FF_SAVE_FRAME=99999 FF_STOP=60000 FF_LOAD="$2" FF_RAMOUT="$3"
mkdir -p "$out/tmp"
cd "$run" || exit 1
exec mame ffightuc -rompath "${FF_ROMS:-$HOME/mame-roms}" -cfg_directory "$run/cfg" -nvram_directory "$run/nvram" \
  -state_directory "$run/sta" -snapshot_directory "$run/snap" -video none -sound none -nothrottle -seconds_to_run 900 -autoboot_script "$here/ramdump.lua"
