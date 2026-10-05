#!/bin/sh
# ffrun.sh <script.lua> [seconds] : copy of reversing/finalfight/ffrun.sh with run= from FFD_RUN (default scratchpad/finalfight/twoplayer/run) and FF_DIR = this directory lua/
d=$(cd "$(dirname "$0")/.." && pwd)
. "$d/run/env.sh"
run="$runroot"
export FF_DIR="$d/lua"
export FF_OUT=${FF_OUT:-$out}
mkdir -p "$run/cfg" "$run/nvram" "$run/sta" "$run/snap" "$FF_OUT/tmp"
export SDL_VIDEODRIVER=dummy
cd "$run" || exit 1
exec mame ffightuc -rompath "${FF_ROMS:-$HOME/mame-roms}" -cfg_directory "$run/cfg" \
  -nvram_directory "$run/nvram" -state_directory "$run/sta" -snapshot_directory "$run/snap" \
  -video none -sound none -nothrottle ${FF_MAMEARGS} -seconds_to_run "${2:-120}" -autoboot_script "$1"
