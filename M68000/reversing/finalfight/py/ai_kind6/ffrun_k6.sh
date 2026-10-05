#!/bin/sh
# MAME wrapper for the kind-6 harness: lua/ from reversing/finalfight, own MAME run directory.
#   K6_RUN_DIR=<dir> (default <M68000>/scratchpad/finalfight/p3/d/run; holds cfg, nvram, sta/ffightuc/<state>.sta, snap, outputs)
#   ffrun_k6.sh <script.lua> [seconds]     FF_MAMEARGS="-debug -debugger none" for k6hit.lua
dir=$(cd "$(dirname "$0")" && pwd)
here=$(cd "$dir/../.." && pwd)
root=$(cd "$here/../.." && pwd)
run=${K6_RUN_DIR:-$root/scratchpad/finalfight/p3/d/run}
export K6_RUN_DIR="$run"
export FF_DIR="$here/lua"
export FF_OUT=${FF_OUT:-$run}
mkdir -p "$run/cfg" "$run/nvram" "$run/sta/ffightuc" "$run/snap" "$FF_OUT/tmp"
export SDL_VIDEODRIVER=dummy
cd "$run" || exit 1
exec mame ffightuc -rompath "${FF_ROMS:-$HOME/mame-roms}" -cfg_directory "$run/cfg" \
  -nvram_directory "$run/nvram" -state_directory "$run/sta" -snapshot_directory "$run/snap" \
  -video none -sound none -nothrottle ${FF_MAMEARGS} -seconds_to_run "${2:-120}" -autoboot_script "$1"
